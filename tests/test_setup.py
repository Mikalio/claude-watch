import json
import subprocess
from pathlib import Path

import pytest

from wristling import setup

HOOK = setup.our_hook("http://relay:8079")


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "HOME", tmp_path / "wristling")
    monkeypatch.setattr(setup, "CLAUDE_SETTINGS", tmp_path / "claude" / "settings.json")
    return tmp_path


def answers(monkeypatch, *replies):
    queue = list(replies)
    monkeypatch.setattr("builtins.input", lambda prompt="": queue.pop(0))
    return queue


class FakeRun:
    """Stands in for setup.run: answers each command by its first words and keeps what was run."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def __call__(self, cmd, capture=True, check=True, input=None, cwd=None):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        for start, (code, out) in self.replies.items():
            if " ".join([Path(cmd[0]).name, *cmd[1:]]).startswith(start):
                if check and code:
                    raise setup.SetupError(f"{start} failed")
                return subprocess.CompletedProcess(cmd, code, out, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")


def ok(result):
    return 0, json.dumps({"status": "success", "result": result})


def test_hooks_go_in_for_every_event_but_session_start():
    settings = setup.with_hooks({}, "http://relay:8079/")
    assert set(settings["hooks"]) == set(setup.HOOK_EVENTS)
    assert "SessionStart" not in settings["hooks"]
    assert settings["hooks"]["Stop"] == [{"hooks": [HOOK]}]
    assert HOOK["url"] == "http://relay:8079/hook?where=pc"


def test_hooks_replace_our_old_ones_and_keep_everything_else():
    theirs = {"type": "command", "command": "echo hi"}
    old = setup.our_hook("http://old:8079")
    settings = {"model": "opus", "hooks": {
        "Stop": [{"hooks": [theirs, old]}],
        "PreToolUse": [{"matcher": "Bash", "hooks": [old]}],
        "SessionStart": [{"hooks": [theirs]}],
    }}
    new = setup.with_hooks(settings, "http://relay:8079")
    assert new["model"] == "opus"
    assert new["hooks"]["Stop"] == [{"hooks": [theirs]}, {"hooks": [HOOK]}]
    assert new["hooks"]["PreToolUse"] == [{"hooks": [HOOK]}]
    assert new["hooks"]["SessionStart"] == [{"hooks": [theirs]}]
    assert settings["hooks"]["Stop"] == [{"hooks": [theirs, old]}], "the input is left alone"
    assert setup.with_hooks(new, "http://relay:8079") == new, "running it twice changes nothing"


def test_firebase_json_reads_the_result_after_any_noise(monkeypatch):
    monkeypatch.setattr(setup, "run", FakeRun({"firebase apps:list": (0, "Update available\n" + ok([{"appId": "1:2"}])[1])}))
    assert setup.firebase_json("firebase", "apps:list") == [{"appId": "1:2"}]


def test_firebase_json_says_what_failed(monkeypatch):
    monkeypatch.setattr(setup, "run", FakeRun({"firebase": (1, json.dumps({"status": "error", "error": "Not in quota"}))}))
    with pytest.raises(setup.SetupError, match="Not in quota"):
        setup.firebase_json("firebase", "projects:create", "x")


def test_the_package_comes_from_the_build_file():
    assert setup.application_id("face") == setup.application_id("app") + ".face"


def test_firebase_makes_a_project_and_an_app(home, monkeypatch):
    fake = FakeRun({
        "firebase projects:list": (0, ""),
        "firebase projects:create": ok({"projectId": "x"}),
        "firebase apps:list": ok([]),
        "firebase apps:create": ok({"appId": "1:99:android:ab"}),
        "firebase apps:sdkconfig": ok({"fileName": "google-services.json", "fileContents": '{"project_info": {}}'}),
    })
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup.shutil, "which", lambda tool: f"/bin/{tool}")
    answers(monkeypatch, "")
    state = {}
    setup.step_firebase(state)
    assert state["project"].startswith("wristling-") and len(state["project"]) == 16
    assert state["package"] == setup.application_id("app")
    created = next(c for c in fake.calls if c[1] == "apps:create")
    assert created[created.index("--package-name") + 1] == state["package"]
    assert (setup.HOME / "google-services.json").read_text() == '{"project_info": {}}'


def test_firebase_reuses_an_app_that_is_there(home, monkeypatch):
    package = setup.application_id("app")
    fake = FakeRun({
        "firebase apps:list": ok([{"appId": "1:2:android:old", "packageName": package}]),
        "firebase apps:sdkconfig": ok({"fileContents": "{}"}),
    })
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup.shutil, "which", lambda tool: f"/bin/{tool}")
    answers(monkeypatch, "my-project")
    setup.step_firebase({})
    assert not any(c[1] in ("apps:create", "projects:create") for c in fake.calls)
    assert ["/bin/firebase", "apps:sdkconfig", "ANDROID", "1:2:android:old", "--project", "my-project", "--json"] in fake.calls


def test_a_downloaded_key_is_checked_and_copied(home, monkeypatch):
    monkeypatch.setattr(setup.shutil, "which", lambda tool: None)
    downloaded = home / "key.json"
    downloaded.write_text(json.dumps({"type": "service_account", "project_id": "other"}))
    answers(monkeypatch, str(downloaded))
    with pytest.raises(setup.SetupError, match="isn't a service account key for mine"):
        setup.step_key({"project": "mine"})
    downloaded.write_text(json.dumps({"type": "service_account", "project_id": "mine"}))
    answers(monkeypatch, f'"{downloaded}"')
    setup.step_key({"project": "mine"})
    assert json.loads((setup.HOME / "firebase-key.json").read_text())["project_id"] == "mine"


def test_the_server_folder_holds_what_the_relay_needs(home, monkeypatch):
    (home / "wristling").mkdir()
    (home / "wristling" / "firebase-key.json").write_text("{}")
    monkeypatch.setattr(setup, "wait_for_relay", lambda url: True)
    answers(monkeypatch, "3", "", "10.0.0.20")
    state = {}
    setup.step_relay(state)
    folder = setup.HOME / "relay"
    assert (folder / "src" / "Dockerfile").exists() and (folder / "src" / "relay" / "web.py").exists()
    assert not list(folder.rglob("__pycache__"))
    assert (folder / "data" / "firebase-key.json").read_text() == "{}"
    assert (folder / "relay.env").read_text() == f"RELAY_TOKEN={state['token']}\nFCM_TOPIC={state['topic']}\nPUSH_KEY={state['push_key']}\n"
    assert "--env-file relay.env" in (folder / "run.sh").read_text()
    assert state["relay_url"] == "http://10.0.0.20:8079"
    assert state["topic"].startswith("wristling-") and len(state["token"]) >= 40


def test_the_build_stops_on_a_copy_with_a_fixed_topic():
    if "wristlingTopic" in (setup.ROOT / "watch" / "app" / "build.gradle.kts").read_text():
        pytest.skip("this copy reads the topic at build time")
    with pytest.raises(setup.SetupError, match="public repo"):
        setup.step_build({})


def test_a_github_build_refuses_a_public_repo(home, monkeypatch):
    monkeypatch.setattr(setup.shutil, "which", lambda tool: f"/bin/{tool}")
    monkeypatch.setattr(setup, "run", FakeRun({"gh api user": (0, "someone\n"), "gh repo view": (0, "PUBLIC\n")}))
    answers(monkeypatch, "")
    with pytest.raises(setup.SetupError, match="isn't private"):
        setup.build_on_github({"topic": "t"}, home / "apk")


def test_a_github_build_sets_the_secrets_before_pushing(home, monkeypatch):
    (home / "wristling").mkdir()
    (home / "wristling" / "google-services.json").write_text("{}")
    fake = FakeRun({
        "gh api user": (0, "someone\n"),
        "gh repo view": (1, ""),
        "git -C": (0, "abc123\n"),
        "git ls-remote": (0, ""),
        "gh run list": (0, json.dumps([{"databaseId": 7, "createdAt": "2999-01-01T00:00:00Z"}])),
    })
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup.shutil, "which", lambda tool: f"/bin/{tool}")
    answers(monkeypatch, "")
    state = {"topic": "wristling-abc", "push_key": "a-key"}
    setup.build_on_github(state, home / "apk")
    assert ["/bin/gh", "secret", "set", "PUSH_KEY", "-R", "someone/wristling-build", "--body", "a-key"] in fake.calls
    secrets_at = max(i for i, c in enumerate(fake.calls) if c[1:3] == ["secret", "set"])
    push_at = next(i for i, c in enumerate(fake.calls) if "push" in c)
    assert secrets_at < push_at
    assert ["/bin/gh", "secret", "set", "FCM_TOPIC", "-R", "someone/wristling-build", "--body", "wristling-abc"] in fake.calls
    assert any(c[1:2] == ["repo"] and "--private" in c for c in fake.calls)
    assert fake.calls[-1][:3] == ["/bin/gh", "run", "download"] and "7" in fake.calls[-1]
    assert state["build_repo"] == "someone/wristling-build"


def test_the_watch_step_disconnects_even_when_an_install_fails(home, monkeypatch):
    fake = FakeRun({"adb connect": (0, "connected to 10.0.0.5:5555\n"), "adb -s 10.0.0.5:5555 install -r face": (1, "")})
    monkeypatch.setattr(setup, "run", lambda cmd, **kw: fake([Path(str(cmd[0])).name, *cmd[1:]], **kw))
    monkeypatch.setattr(setup, "find_adb", lambda: "adb")
    answers(monkeypatch, "n", "10.0.0.5:5555")
    with pytest.raises(setup.SetupError):
        setup.step_watch({"apks": {"app": "app.apk", "face": "face.apk"}})
    assert fake.calls[-2:] == [["adb", "disconnect", "10.0.0.5:5555"], ["adb", "kill-server"]]


def test_the_watch_step_installs_both_and_sets_the_face(home, monkeypatch):
    fake = FakeRun({"adb connect": (0, "connected to 10.0.0.5:5555\n")})
    monkeypatch.setattr(setup, "run", lambda cmd, **kw: fake([Path(str(cmd[0])).name, *cmd[1:]], **kw))
    monkeypatch.setattr(setup, "find_adb", lambda: "adb")
    answers(monkeypatch, "y", "10.0.0.5:37000", "123456", "10.0.0.5:5555")
    setup.step_watch({"apks": {"app": "app.apk", "face": "face.apk"}})
    assert ["adb", "pair", "10.0.0.5:37000", "123456"] in fake.calls
    assert ["adb", "-s", "10.0.0.5:5555", "install", "-r", "app.apk"] in fake.calls
    assert setup.application_id("face") in fake.calls[-3]


def test_setup_carries_on_where_it_stopped(home, monkeypatch):
    ran = []
    for step in setup.STEPS:
        monkeypatch.setitem(setup.RUNNERS, step, lambda state, step=step: ran.append(step))

    def stop(state):
        raise setup.SetupError("no Docker")

    monkeypatch.setitem(setup.RUNNERS, "relay", stop)
    assert setup.main([]) == 1
    assert ran == ["firebase", "key"]
    monkeypatch.setitem(setup.RUNNERS, "relay", lambda state: ran.append("relay"))
    assert setup.main([]) == 0
    assert ran == ["firebase", "key", "relay", "hooks", "build", "watch"]
    assert setup.main(["--redo", "hooks"]) == 0
    assert ran[-1] == "hooks"


def test_the_plugin_has_the_same_hooks_as_the_settings_and_starts_the_relay():
    hooks = json.loads((setup.ROOT / "plugin" / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    start = hooks.pop("SessionStart")[0]["hooks"][0]
    assert start["type"] == "command" and "start_relay.py" in start["command"]
    assert sorted(hooks) == sorted(setup.HOOK_EVENTS)
    want = setup.our_hook(setup.LOCAL_RELAY)
    assert all(groups == [{"hooks": [want]}] for groups in hooks.values())


def test_a_relay_on_this_pc_gets_the_plugin_and_no_hooks_in_the_settings(home, monkeypatch):
    setup.CLAUDE_SETTINGS.parent.mkdir(parents=True)
    theirs = {"type": "command", "command": "theirs"}
    old = setup.with_hooks({"hooks": {"Stop": [{"hooks": [theirs]}]}}, "http://relay:8079")
    setup.CLAUDE_SETTINGS.write_text(json.dumps(old), encoding="utf-8")
    fake = FakeRun({})
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup, "need", lambda tool, how: tool)
    monkeypatch.setattr(setup, "save_token_variable", lambda token: "done")
    setup.step_hooks({"relay_where": "pc", "relay_url": setup.LOCAL_RELAY, "token": "t"})
    assert json.loads(setup.CLAUDE_SETTINGS.read_text(encoding="utf-8")) == {"hooks": {"Stop": [{"hooks": [theirs]}]}}
    assert ["claude", "plugin", "install", "wristling@wristling"] in fake.calls


def test_a_relay_elsewhere_gets_hooks_and_loses_the_plugin(home, monkeypatch):
    fake = FakeRun({})
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup.shutil, "which", lambda tool: tool)
    monkeypatch.setattr(setup, "save_token_variable", lambda token: "done")
    setup.step_hooks({"relay_url": "http://relay:8079", "token": "t"})
    assert "UserPromptSubmit" in json.loads(setup.CLAUDE_SETTINGS.read_text(encoding="utf-8"))["hooks"]
    assert ["claude", "plugin", "uninstall", "wristling@wristling"] in fake.calls


def test_the_relay_on_this_pc_is_set_up_and_started(home, monkeypatch):
    answers(monkeypatch, "1")
    fake = FakeRun({})
    monkeypatch.setattr(setup, "run", fake)
    monkeypatch.setattr(setup, "wait_for_relay", lambda url: True)
    state = {}
    setup.step_relay(state)
    assert state["relay_where"] == "pc" and state["relay_url"] == setup.LOCAL_RELAY
    assert (setup.HOME / "pc" / "relay" / "web.py").exists()
    saved = json.loads((setup.HOME / "state.json").read_text(encoding="utf-8"))
    assert saved["token"] == state["token"] and saved["topic"] == state["topic"]
    assert any(c[-1].endswith("start_relay.py") for c in fake.calls)


def test_choosing_docker_afterwards_forgets_the_relay_on_this_pc(home, monkeypatch):
    answers(monkeypatch, "4", "http://relay:8079", "tok", "top", "")
    monkeypatch.setattr(setup, "wait_for_relay", lambda url: True)
    state = {"relay_where": "pc"}
    setup.step_relay(state)
    assert "relay_where" not in state and state["relay_url"] == "http://relay:8079"
