import base64
import json

import pytest
from fastapi.testclient import TestClient

from relay.push import Relay, android_options, seal
from relay.sessions import Sessions
from relay.web import create_app, push_key

TOKEN = "test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


class FakeSender:
    def __init__(self):
        self.sent = []
        self.wakes = []

    def send(self, data, wake):
        self.sent.append(data)
        self.wakes.append(wake)


def make():
    clock, sender = Clock(), FakeSender()
    relay = Relay(Sessions(clock=clock), sender, keepalive_min=15, clock=clock)
    return TestClient(create_app(relay=relay, token=TOKEN)), relay, sender, clock


def hook(client, name, sid="a", where="pc", **extra):
    body = {"hook_event_name": name, "session_id": sid, "cwd": "C:\\Code\\Grocery offers", **extra}
    return client.post(f"/hook?where={where}", json=body, headers=AUTH)


def test_hooks_need_the_token():
    client, *_ = make()
    assert client.post("/hook", json={}).status_code == 401
    assert client.post("/hook", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/state").status_code == 401
    assert client.get("/health").status_code == 200


def test_a_hook_gets_an_empty_answer_and_moves_the_state():
    client, *_ = make()
    response = hook(client, "UserPromptSubmit", where="cloud")
    assert response.status_code == 204 and response.content == b""
    state = client.get("/state", headers=AUTH).json()
    assert (state["state"], state["where"]) == ("working", "Cloud")


def test_pushes_only_when_the_watch_would_change():
    client, _, sender, _ = make()
    hook(client, "UserPromptSubmit")
    hook(client, "PreToolUse")
    hook(client, "PostToolUse")
    assert len(sender.sent) == 1
    hook(client, "PermissionRequest")
    assert len(sender.sent) == 2
    message = sender.sent[-1]
    assert message["state"] == "needs" and message["needs"] == "1" and message["working"] == "0"
    assert json.loads(message["sessions"])[0]["project"] == "Grocery offers"
    assert all(isinstance(value, str) for value in message.values())


def test_only_a_push_that_calls_for_you_wakes_the_watch():
    client, relay, sender, clock = make()
    hook(client, "UserPromptSubmit")
    hook(client, "PermissionRequest")
    hook(client, "PostToolUse")
    hook(client, "Stop")
    assert [m["state"] for m in sender.sent] == ["working", "needs", "working", "done"]
    assert sender.wakes == [False, True, False, True]
    clock.now += 11 * 60  # "your turn" fades
    relay.push()
    assert sender.sent[-1]["state"] == "sleeping" and sender.wakes[-1] is False


def test_small_changes_wait_and_go_together():
    client, relay, sender, clock = make()
    hook(client, "UserPromptSubmit")
    hook(client, "UserPromptSubmit", sid="b")
    hook(client, "SubagentStart", sid="b", agent_id="x")
    assert len(sender.sent) == 1
    clock.now += 2 * 60
    relay.push()
    assert len(sender.sent) == 2
    message = sender.sent[-1]
    assert (message["working"], message["agents"]) == ("2", "1")
    assert sender.wakes[-1] is False
    relay.push()
    assert len(sender.sent) == 2


def test_a_second_session_with_your_turn_cant_wait():
    client, _, sender, clock = make()
    hook(client, "Stop", sid="a")
    clock.now += 5
    body = {"hook_event_name": "Stop", "session_id": "b", "cwd": "C:\\Code\\Trip planner"}
    client.post("/hook", json=body, headers=AUTH)
    assert len(sender.sent) == 2
    assert (sender.sent[-1]["project"], sender.sent[-1]["done"]) == ("Trip planner", "2")
    assert sender.wakes[-1] is True


def test_your_turn_waits_while_another_session_works():
    client, relay, sender, clock = make()
    hook(client, "UserPromptSubmit", sid="a")
    hook(client, "Stop", sid="b")
    assert len(sender.sent) == 1
    clock.now += 2 * 60
    relay.push()
    assert (sender.sent[-1]["state"], sender.sent[-1]["done"]) == ("working", "1")
    assert sender.wakes[-1] is False
    hook(client, "Stop", sid="a")  # nothing is working any more: now the word changes and it wakes
    assert (sender.sent[-1]["state"], sender.sent[-1]["done"]) == ("done", "2")
    assert sender.wakes[-1] is True


def test_a_session_waiting_for_agents_sends_no_push():
    client, _, sender, _ = make()
    hook(client, "UserPromptSubmit")
    hook(client, "SubagentStart", agent_id="x")
    hook(client, "Stop", background_tasks=[{"id": "x", "type": "subagent", "status": "running", "description": "d"}])
    hook(client, "PreToolUse", agent_id="x")
    assert [m["state"] for m in sender.sent] == ["working"]


def test_keepalive_while_busy_but_not_while_sleeping():
    client, relay, sender, clock = make()
    hook(client, "UserPromptSubmit")
    clock.now += 16 * 60
    relay.push()
    assert len(sender.sent) == 2
    hook(client, "SessionEnd")
    assert sender.sent[-1]["state"] == "sleeping"
    clock.now += 60 * 60
    relay.push()
    assert len(sender.sent) == 3


def test_a_failed_push_is_tried_again():
    client, relay, sender, _ = make()

    def broken(data, wake):
        raise OSError("no network")

    sender.send = broken
    hook(client, "UserPromptSubmit")
    sender.send = FakeSender.send.__get__(sender)
    relay.push()
    assert sender.sent[-1]["state"] == "working"


def test_bad_json_is_refused():
    client, *_ = make()
    response = client.post("/hook", content=b"not json", headers={**AUTH, "Content-Type": "application/json"})
    assert response.status_code == 400


def test_a_push_that_wakes_skips_firebases_burst_limit():
    assert "collapse_key" not in android_options(wake=True)
    assert android_options(wake=True)["priority"] == "HIGH"
    quiet = android_options(wake=False)
    assert quiet["collapse_key"] == "state" and quiet["priority"] == "NORMAL"


# The same push and key as watch/app/src/test/.../SealedTest.kt, so the two sides can't drift apart
PUSH_KEY = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
SEALED = "ZGVmZ2hpamtsbW5vMzmtEhidM7wEQDGNvwEZ327gdnjkBpYR0/OWarzRyivxmzngI3T9YY+AWkIoAjoCqK5TgmdmYbAB7TD2"


def test_a_sealed_push_is_what_the_watch_expects():
    data = {"state": "needs", "project": "Grocery offers"}
    assert seal(data, PUSH_KEY, nonce=bytes(range(100, 112))) == {"sealed": SEALED}


def test_each_sealed_push_is_different_and_hides_the_names():
    data = {"state": "needs", "project": "Grocery offers"}
    first, second = seal(data, PUSH_KEY), seal(data, PUSH_KEY)
    assert first != second and list(first) == ["sealed"]
    assert b"Grocery" not in base64.b64decode(first["sealed"])


def test_a_push_key_of_the_wrong_length_stops_the_relay(monkeypatch):
    monkeypatch.setenv("PUSH_KEY", base64.b64encode(b"short").decode())
    with pytest.raises(RuntimeError):
        push_key()
