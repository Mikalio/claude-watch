"""Sets Wristling up, step by step: python -m wristling setup

Everything stays yours: your own Firebase project, your own relay, your own build of the watch app. The steps:

  firebase  create (or pick) a Firebase project and its Android app, and save google-services.json
  key       save the service account key the relay sends pushes with
  relay     start the relay on this PC (no Docker needed), in Docker, or write what a server needs to run it
  hooks     add Claude Code's hooks: a plugin for a relay on this PC, otherwise ~/.claude/settings.json
  build     build the watch app and face, in a private copy on your GitHub or on this PC
  watch     install both on the watch over wireless debugging, set the face, disconnect

Each finished step is kept in ~/.wristling/state.json, so running setup again carries on where it stopped.
--redo STEP runs that step again. Left to you: signing in to Google (and GitHub, for a GitHub build), and turning
on wireless debugging on the watch.

Only Python's standard library is used, so a plain Python 3.10 or newer runs it.
"""

import argparse
import base64
import calendar
import copy
import json
import os
import platform
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("WRISTLING_HOME") or Path.home() / ".wristling")
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
TOKEN_VAR = "WRISTLING_TOKEN"
STEPS = ["firebase", "key", "relay", "hooks", "build", "watch"]
RELAY_PORT = 8079
LOCAL_RELAY = f"http://127.0.0.1:{RELAY_PORT}"
PLUGIN = "wristling"
ARTIFACT = "wristling-debug"  # the download the "Watch app" workflow keeps

# SessionStart is left out: Claude Code runs no http hooks on it, so a session appears at its first prompt instead
HOOK_EVENTS = ["UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest", "Elicitation",
               "Notification", "Stop", "StopFailure", "SubagentStart", "SubagentStop", "SessionEnd"]


class SetupError(Exception):
    """A step can't go on. The message says what to do about it."""


# ── Small helpers ─────────────────────────────────────────────────────────────


def say(text: str = "") -> None:
    print(text, flush=True)


def ask(question: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    answer = input(f"{question}{hint}: ").strip()
    return answer or (default or "")


def choose(question: str, options: dict[str, str]) -> str:
    """Asks for one of the options by number and returns its key."""
    keys = list(options)
    say(question)
    for number, key in enumerate(keys, 1):
        say(f"  {number}. {options[key]}")
    while True:
        answer = ask("Number", "1")
        if answer.isdigit() and 1 <= int(answer) <= len(keys):
            return keys[int(answer) - 1]


def yes(question: str) -> bool:
    return ask(f"{question} (y/n)", "y").lower().startswith("y")


def run(cmd: list, capture: bool = True, check: bool = True, input: str | None = None, cwd: Path | None = None):
    """Runs a command. With capture=False its output and prompts go straight to the terminal."""
    result = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True, input=input, cwd=cwd)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise SetupError(f"{Path(str(cmd[0])).name} {' '.join(str(c) for c in cmd[1:3])} failed" + (f":\n{detail}" if detail else ""))
    return result


def need(tool: str, how: str) -> str:
    """The full path of a command-line tool, so .cmd shims work on Windows too."""
    path = shutil.which(tool)
    if not path:
        raise SetupError(f"{tool} isn't installed. {how}\nThen run setup again.")
    return path


def random_id(length: int) -> str:
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def write_private(path: Path, text: str) -> None:
    """Writes a secret file only you can read (on Windows, your profile folder already sees to that)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def load_state() -> dict:
    try:
        return json.loads((HOME / "state.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"done": []}


def save_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        HOME.chmod(0o700)
    write_private(HOME / "state.json", json.dumps(state, indent=2))


def application_id(module: str) -> str:
    """The package name in watch/<module>/build.gradle.kts."""
    text = (ROOT / "watch" / module / "build.gradle.kts").read_text(encoding="utf-8")
    match = re.search(r'applicationId\s*=\s*"([^"]+)"', text)
    if not match:
        raise SetupError(f"No applicationId in watch/{module}/build.gradle.kts")
    return match.group(1)


def ensure_secrets(state: dict) -> None:
    """The topic the relay sends to and the watch listens on, the token the hooks send, and the key that seals
    the pushes so only the watch can read them, not Firebase. Made once."""
    state.setdefault("topic", "wristling-" + secrets.token_hex(16))
    state.setdefault("token", secrets.token_urlsafe(32))
    state.setdefault("push_key", base64.b64encode(secrets.token_bytes(32)).decode())


# ── Firebase ──────────────────────────────────────────────────────────────────


def firebase_json(firebase: str, *args: str):
    """Runs a Firebase CLI command with --json and returns its result."""
    result = run([firebase, *args, "--json"], check=False)
    text = result.stdout or ""
    try:
        answer = json.loads(text[text.index("{"):])
    except ValueError:
        raise SetupError(f"firebase {args[0]} gave no answer:\n{(result.stderr or text).strip()}")
    if answer.get("status") != "success":
        raise SetupError(f"firebase {args[0]} failed: {answer.get('error', answer)}")
    return answer.get("result")


def step_firebase(state: dict) -> None:
    firebase = need("firebase", "Install the Firebase CLI: npm install -g firebase-tools, or see https://firebase.google.com/docs/cli")
    if run([firebase, "projects:list", "--json"], check=False).returncode != 0:
        say("Sign in to Google for Firebase. A browser opens.")
        run([firebase, "login"], capture=False)

    project = ask("Firebase project ID to use (press Enter to make a new one)")
    if not project:
        project = "wristling-" + random_id(6)
        say(f"Making the Firebase project {project}. This takes a minute.")
        firebase_json(firebase, "projects:create", project, "--display-name", "Wristling")

    package = application_id("app")
    apps = firebase_json(firebase, "apps:list", "ANDROID", "--project", project) or []
    app = next((a for a in apps if a.get("packageName") == package), None)
    if app is None:
        say(f"Adding the Android app {package}.")
        app = firebase_json(firebase, "apps:create", "ANDROID", "Wristling", "--package-name", package, "--project", project)
    config = firebase_json(firebase, "apps:sdkconfig", "ANDROID", app["appId"], "--project", project)
    write_private(HOME / "google-services.json", config["fileContents"])
    state.update(project=project, package=package)
    say(f"Saved the app's Firebase config to {HOME / 'google-services.json'}.")


def check_key(path: Path, project: str) -> None:
    try:
        key = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SetupError(f"{path} isn't a key file")
    if key.get("type") != "service_account" or key.get("project_id") != project:
        raise SetupError(f"{path} isn't a service account key for {project}")


def step_key(state: dict) -> None:
    project, key = state["project"], HOME / "firebase-key.json"
    gcloud = shutil.which("gcloud")
    if gcloud and yes("Make the key with the gcloud CLI you have installed?"):
        if not run([gcloud, "auth", "list", "--format=value(account)"]).stdout.strip():
            run([gcloud, "auth", "login"], capture=False)
        # On by default in new Firebase projects, as far as we know; turning it on again does no harm
        run([gcloud, "services", "enable", "fcm.googleapis.com", "--project", project], check=False)
        found = run([gcloud, "iam", "service-accounts", "list", "--project", project,
                     "--filter=email:adminsdk", "--format=value(email)"]).stdout.split()
        if found:
            run([gcloud, "iam", "service-accounts", "keys", "create", key, "--iam-account", found[0], "--project", project])
            if os.name != "nt":
                key.chmod(0o600)
    if not key.exists():
        say(f"Open https://console.firebase.google.com/project/{project}/settings/serviceaccounts/adminsdk")
        say("press 'Generate new private key', and save the file.")
        downloaded = Path(ask("Where you saved it").strip('"'))
        check_key(downloaded, project)
        write_private(key, downloaded.read_text(encoding="utf-8"))
        say(f"Copied. Delete {downloaded} when setup is done: anyone with it can send pushes to your watch.")
    check_key(key, project)
    say(f"Saved the key to {key}. Keep it out of Git.")


# ── Relay ─────────────────────────────────────────────────────────────────────


def relay_files(folder: Path, state: dict, posix_ids: bool) -> None:
    """Everything a machine with Docker needs to build and run the relay: its code, the key and its settings."""
    for name in ("Dockerfile", "requirements.txt"):
        (folder / "src").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, folder / "src" / name)
    shutil.copytree(ROOT / "relay", folder / "src" / "relay", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    write_private(folder / "data" / "firebase-key.json", (HOME / "firebase-key.json").read_text(encoding="utf-8"))
    settings = f"RELAY_TOKEN={state['token']}\nFCM_TOPIC={state['topic']}\nPUSH_KEY={state['push_key']}\n"
    if posix_ids:
        settings += f"PUID={os.getuid()}\nPGID={os.getgid()}\n"
    write_private(folder / "relay.env", settings)


RUN_SH = f"""#!/bin/sh
# Builds and starts the Wristling relay. Run it again after updating src/.
set -e
cd "$(dirname "$0")"
docker build -t wristling-relay src
docker rm -f wristling-relay 2>/dev/null || true
# The relay runs as you, so it can read the key that only you can read
docker run -d --name wristling-relay --restart unless-stopped -p {RELAY_PORT}:8000 \\
  -v "$PWD/data:/data:ro" --env-file relay.env -e PUID="$(id -u)" -e PGID="$(id -g)" wristling-relay
sleep 3
curl -fsS http://localhost:{RELAY_PORT}/health && echo " relay is up"
"""


def wait_for_relay(url: str, seconds: int = 30) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=3):
                return True
        except (OSError, urllib.error.URLError):
            time.sleep(2)
    return False


def venv_python() -> Path:
    return HOME / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def relay_on_this_pc(state: dict) -> None:
    """The relay in its own Python environment in HOME. The plugin's SessionStart hook keeps it running."""
    start = ROOT / "plugin" / "scripts" / "start_relay.py"
    run([sys.executable, start, "--stop"], check=False)
    if not venv_python().exists():
        say(f"Making a Python environment for the relay in {HOME / 'venv'}.")
        run([sys.executable, "-m", "venv", HOME / "venv"])
    run([venv_python(), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", ROOT / "requirements.txt"])
    shutil.copytree(ROOT / "relay", HOME / "pc" / "relay", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    state.update(relay_where="pc", relay_url=LOCAL_RELAY)
    save_state(state)  # the start script reads the token and topic from here
    run([sys.executable, start])


def step_relay(state: dict) -> None:
    ensure_secrets(state)
    where = choose("Where will the relay run? It must be on while you use Claude Code.", {
        "pc": "On this PC, no Docker. It starts with Claude Code. If this PC sleeps mid-session, the watch only finds out after 40 minutes",
        "here": "On this PC, in Docker",
        "server": "On a server or NAS with Docker: I'll get a folder to copy there",
        "existing": "I already run a relay",
    })
    state.pop("relay_where", None)
    folder = HOME / "relay"
    if where == "pc":
        relay_on_this_pc(state)
    elif where == "here":
        docker = need("docker", "Install Docker Desktop: https://docs.docker.com/get-docker/")
        relay_files(folder, state, posix_ids=os.name != "nt")
        say("Building and starting the relay.")
        run([docker, "build", "-t", "wristling-relay", folder / "src"], capture=False)
        run([docker, "rm", "-f", "wristling-relay"], check=False)
        run([docker, "run", "-d", "--name", "wristling-relay", "--restart", "unless-stopped", "-p", f"{RELAY_PORT}:8000",
             "-v", f"{folder / 'data'}:/data:ro", "--env-file", folder / "relay.env", "wristling-relay"])
        state["relay_url"] = f"http://localhost:{RELAY_PORT}"
    elif where == "server":
        relay_files(folder, state, posix_ids=False)
        (folder / "run.sh").write_text(RUN_SH, encoding="utf-8", newline="\n")
        say(f"Copy the folder {folder} to the server and run 'sh run.sh' in it.")
        say("It holds your key and token, so copy it straight there, keep it off shared folders, and keep the relay")
        say("off the open internet: the token is all that protects it.")
        ask("Press Enter once the relay is running")
        host = ask("The server's address on your network (like 10.0.0.20)")
        state["relay_url"] = f"http://{host}:{RELAY_PORT}"
    else:
        state["relay_url"] = ask("The relay's address", f"http://localhost:{RELAY_PORT}").rstrip("/")
        state["token"] = ask("Its RELAY_TOKEN")
        state["topic"] = ask("Its FCM_TOPIC")
        state["push_key"] = ask("Its PUSH_KEY (press Enter if it has none: pushes then stay plain)")
    if wait_for_relay(state["relay_url"]):
        say(f"The relay answers at {state['relay_url']}.")
    else:
        say(f"No answer from {state['relay_url']} yet. The hooks still go in; check the relay before you test.")


# ── Hooks ─────────────────────────────────────────────────────────────────────


def our_hook(relay_url: str) -> dict:
    return {"type": "http", "url": f"{relay_url.rstrip('/')}/hook?where=pc", "timeout": 3,
            "headers": {"Authorization": f"Bearer ${TOKEN_VAR}"}, "allowedEnvVars": [TOKEN_VAR]}


def is_ours(hook: dict) -> bool:
    return hook.get("type") == "http" and TOKEN_VAR in hook.get("allowedEnvVars", [])


def without_hooks(settings: dict) -> dict:
    """The settings without any Wristling hook, everything else kept."""
    settings = copy.deepcopy(settings)
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        groups = []
        for group in hooks[event]:
            kept = [h for h in group.get("hooks", []) if not is_ours(h)]
            if kept:
                groups.append({**group, "hooks": kept})
            elif not group.get("hooks"):
                groups.append(group)
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    return settings


def with_hooks(settings: dict, relay_url: str) -> dict:
    """The settings with one Wristling hook per event. Earlier Wristling hooks are replaced, everything else kept."""
    settings = without_hooks(settings)
    hooks = settings.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        hooks.setdefault(event, []).append({"hooks": [our_hook(relay_url)]})
    return settings


def save_token_variable(token: str) -> str:
    """Keeps the token where Claude Code can read it. Returns what the person still has to do."""
    os.environ[TOKEN_VAR] = token
    if os.name == "nt":
        run(["setx", TOKEN_VAR, token])
        return "Restart Claude Code, and the Claude app if it's open, so they see the new variable."
    profile = Path.home() / (".zshrc" if os.environ.get("SHELL", "").endswith("zsh") else ".bashrc")
    line = f"export {TOKEN_VAR}='{token}'"
    if yes(f"Add the token to {profile}?"):
        with profile.open("a", encoding="utf-8") as file:
            file.write(f"\n# Wristling: the token Claude Code's hooks send to the relay\n{line}\n")
        return f"Open a new terminal before starting Claude Code. The Claude app started from the dock won't see {profile}."
    return f"Make {TOKEN_VAR} available to Claude Code yourself:\n  {line}"


def install_plugin() -> None:
    """The plugin brings the hooks when the relay is on this PC. It's installed from this clone: nothing is downloaded."""
    claude = need("claude", "Install Claude Code's command line, or run setup again and pick a relay in Docker.")
    run([claude, "plugin", "marketplace", "add", ROOT], check=False)  # it fails only if it's there already
    run([claude, "plugin", "marketplace", "update", PLUGIN], check=False)
    run([claude, "plugin", "install", f"{PLUGIN}@{PLUGIN}"])


def remove_plugin() -> None:
    claude = shutil.which("claude")
    if claude:
        run([claude, "plugin", "uninstall", f"{PLUGIN}@{PLUGIN}"], check=False)


def step_hooks(state: dict) -> None:
    try:
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        settings = {}
    except ValueError:
        raise SetupError(f"{CLAUDE_SETTINGS} isn't valid JSON. Fix it, then run setup again.")
    on_this_pc = state.get("relay_where") == "pc"
    wanted = without_hooks(settings) if on_this_pc else with_hooks(settings, state["relay_url"])
    if wanted != settings:
        if CLAUDE_SETTINGS.exists():
            backup = CLAUDE_SETTINGS.with_name(f"settings.before-wristling-{time.strftime('%Y%m%d-%H%M%S')}.json")
            shutil.copyfile(CLAUDE_SETTINGS, backup)
            say(f"Kept a copy of your settings as {backup.name}.")
        CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        CLAUDE_SETTINGS.write_text(json.dumps(wanted, indent=2) + "\n", encoding="utf-8")
    if on_this_pc:
        install_plugin()
        say(f"Installed the {PLUGIN} plugin, which brings the hooks. To remove it: claude plugin uninstall {PLUGIN}@{PLUGIN}")
    else:
        remove_plugin()
        say(f"Added the hooks to {CLAUDE_SETTINGS}.")
    say("A down relay never holds Claude up: the hooks time out after 3 seconds.")
    say(save_token_variable(state["token"]))


# ── Build ─────────────────────────────────────────────────────────────────────


def find_apks(folder: Path) -> dict:
    apks = {name: next(folder.rglob(f"{name}-debug.apk"), None) for name in ("app", "face")}
    if not all(apks.values()):
        raise SetupError(f"The build finished, but both APKs weren't in {folder}")
    return {name: str(path) for name, path in apks.items()}


def latest_run(gh: str, repo: str, sha: str, since: float) -> int | None:
    runs = json.loads(run([gh, "run", "list", "-R", repo, "--workflow", "watch.yml", "--commit", sha,
                           "--json", "databaseId,createdAt", "-L", "5"]).stdout or "[]")
    fresh = [r for r in runs if calendar.timegm(time.strptime(r["createdAt"], "%Y-%m-%dT%H:%M:%SZ")) >= since - 5]
    return max(fresh, key=lambda r: r["createdAt"])["databaseId"] if fresh else None


def build_on_github(state: dict, out: Path) -> None:
    gh = need("gh", "Install the GitHub CLI: https://cli.github.com")
    git = need("git", "Install Git: https://git-scm.com")
    if run([git, "-C", ROOT, "rev-parse", "HEAD"], check=False).returncode != 0:
        raise SetupError("This folder isn't a Git clone. Clone the repo with git, then run setup there.")
    if run([gh, "auth", "status"], check=False).returncode != 0:
        run([gh, "auth", "login"], capture=False)
    login = run([gh, "api", "user", "--jq", ".login"]).stdout.strip()
    repo = state.get("build_repo") or ask("Private repo to build in", f"{login}/wristling-build")
    seen = run([gh, "repo", "view", repo, "--json", "visibility", "--jq", ".visibility"], check=False)
    if seen.returncode == 0 and seen.stdout.strip() != "PRIVATE":
        raise SetupError(f"{repo} isn't private. Its APKs would hold your Firebase config and topic: use a private repo.")
    if seen.returncode != 0:
        run([gh, "repo", "create", repo, "--private",
             "--description", "My own Wristling build. Keep it private: its APKs hold my Firebase config and topic."])
    state["build_repo"] = repo
    # The secrets go in before the code, so the build the push starts already has them
    run([gh, "secret", "set", "GOOGLE_SERVICES_JSON", "-R", repo], input=(HOME / "google-services.json").read_text(encoding="utf-8"))
    run([gh, "secret", "set", "FCM_TOPIC", "-R", repo, "--body", state["topic"]])
    if state.get("push_key"):
        run([gh, "secret", "set", "PUSH_KEY", "-R", repo, "--body", state["push_key"]])
    run([gh, "auth", "setup-git"])

    sha = run([git, "-C", ROOT, "rev-parse", "HEAD"]).stdout.strip()
    url = f"https://github.com/{repo}.git"
    since = time.time()
    remote = run([git, "ls-remote", url, "refs/heads/main"], check=False).stdout.split()
    if remote and remote[0] == sha:
        run([gh, "workflow", "run", "watch.yml", "-R", repo, "--ref", "main"])
    else:
        say(f"Copying this repo's checked-out commit to {repo}.")
        run([git, "-C", ROOT, "push", "--force", url, "HEAD:refs/heads/main"])
    run_id = None
    for _ in range(30):
        run_id = latest_run(gh, repo, sha, since)
        if run_id:
            break
        time.sleep(3)
    if not run_id:
        raise SetupError(f"No build started on {repo}. Check its Actions tab, then run setup again.")
    say(f"Building on GitHub, about 5 minutes: https://github.com/{repo}/actions/runs/{run_id}")
    run([gh, "run", "watch", run_id, "-R", repo, "--exit-status"], capture=False)
    shutil.rmtree(out, ignore_errors=True)
    run([gh, "run", "download", run_id, "-R", repo, "-n", ARTIFACT, "-D", out])


def build_here(state: dict, out: Path) -> None:
    gradle = need("gradle", "Install JDK 17, the Android SDK and Gradle 8.11.1, or build on GitHub instead.")
    shutil.copyfile(HOME / "google-services.json", ROOT / "watch" / "app" / "google-services.json")
    run([gradle, "assembleDebug", "--no-daemon", f"-PwristlingTopic={state['topic']}", f"-PwristlingPushKey={state.get('push_key', '')}"], capture=False, cwd=ROOT / "watch")
    shutil.rmtree(out, ignore_errors=True)
    for module in ("app", "face"):
        shutil.copytree(ROOT / "watch" / module / "build" / "outputs" / "apk" / "debug", out / module)


def step_build(state: dict) -> None:
    if "wristlingTopic" not in (ROOT / "watch" / "app" / "build.gradle.kts").read_text(encoding="utf-8"):
        raise SetupError("This copy builds with a fixed topic. Run setup from a clone of the public repo.")
    how = choose("Where should your watch app be built?", {
        "github": "In a private repo on your GitHub (needs the gh CLI; nothing Android on this PC)",
        "here": "On this PC (needs JDK 17, the Android SDK and Gradle 8.11.1)",
    })
    out = HOME / "apk"
    (build_on_github if how == "github" else build_here)(state, out)
    state["apks"] = find_apks(out)
    say(f"Your APKs are in {out}. Don't share them: they hold your Firebase config and topic.")


# ── Watch ─────────────────────────────────────────────────────────────────────


def find_adb() -> str:
    exe = "adb.exe" if os.name == "nt" else "adb"
    for candidate in (shutil.which("adb"),
                      os.environ.get("ANDROID_HOME") and Path(os.environ["ANDROID_HOME"]) / "platform-tools" / exe,
                      HOME / "platform-tools" / exe):
        if candidate and Path(candidate).exists():
            return str(candidate)
    system = {"Windows": "windows", "Darwin": "darwin"}.get(platform.system(), "linux")
    url = f"https://dl.google.com/android/repository/platform-tools-latest-{system}.zip"
    say("adb isn't installed. Google's platform-tools have it, under the Android SDK terms:")
    say("https://developer.android.com/studio/terms")
    if not yes(f"Download them to {HOME / 'platform-tools'}?"):
        raise SetupError("Install adb (Android platform-tools), then run setup again.")
    archive = HOME / "platform-tools.zip"
    urllib.request.urlretrieve(url, archive)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(HOME)
    archive.unlink()
    adb = HOME / "platform-tools" / exe
    if os.name != "nt":
        adb.chmod(0o755)
    return str(adb)


def step_watch(state: dict) -> None:
    adb = find_adb()
    say("On the watch: Settings, About watch, Software, tap Software version 5 times to unlock Developer options.")
    say("Then Settings, Developer options: turn on ADB debugging and Wireless debugging, and keep the watch")
    say("on the same Wi-Fi as this PC.")
    if yes("Pair this PC with the watch now? (Say no if it's paired already)"):
        say("On the watch: Wireless debugging, Pair new device.")
        pair_at = ask("The IP address and port shown with the code (like 10.0.0.42:37123)")
        run([adb, "pair", pair_at, ask("The pairing code")])
    serial = ask("The IP address and port on the Wireless debugging screen itself")
    if "connected" not in run([adb, "connect", serial]).stdout:
        raise SetupError(f"adb couldn't reach {serial}. Check the address and that the watch is awake.")
    try:
        say("Installing the app and the face.")
        run([adb, "-s", serial, "install", "-r", state["apks"]["app"]])
        run([adb, "-s", serial, "install", "-r", state["apks"]["face"]])
        run([adb, "-s", serial, "shell", "am", "broadcast", "-a", "com.google.android.wearable.app.DEBUG_SURFACE",
             "--es", "operation", "set-watchface", "--es", "watchFaceId", application_id("face")])
    finally:
        # An attached adb drains the watch fast
        run([adb, "disconnect", serial], check=False)
        run([adb, "kill-server"], check=False)
    say("Installed, and the face is set. Turn Wireless debugging off on the watch now: left on, it drains the battery.")


# ── Running the steps ─────────────────────────────────────────────────────────

RUNNERS = {"firebase": step_firebase, "key": step_key, "relay": step_relay, "hooks": step_hooks,
           "build": step_build, "watch": step_watch}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m wristling setup", description="Sets Wristling up, step by step.")
    parser.add_argument("--redo", choices=STEPS, help="run this step again, and the ones after it that aren't done")
    options = parser.parse_args(argv)
    state = load_state()
    if options.redo in state["done"]:
        state["done"].remove(options.redo)
    try:
        for number, step in enumerate(STEPS, 1):
            if step in state["done"]:
                continue
            say(f"\n── {number}/{len(STEPS)} {step} ──")
            RUNNERS[step](state)
            state["done"].append(step)
            save_state(state)
    except SetupError as error:
        save_state(state)
        say(f"\n{error}")
        return 1
    except KeyboardInterrupt:
        save_state(state)
        say("\nStopped. Run setup again to carry on from this step.")
        return 130
    say("\nAll set. Start a Claude Code session and the creature wakes up. If the face says Not connected,")
    say("hold the face and choose Wristling. To redo a step: python -m wristling setup --redo <step>")
    return 0
