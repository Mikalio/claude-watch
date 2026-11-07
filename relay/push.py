"""Sends what the watch shows to the watch, through Firebase Cloud Messaging."""

import json
import logging
import threading
import time

log = logging.getLogger("relay")

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
CALLS_YOU = ("needs", "done")  # the states worth waking a sleeping watch for


def to_message(summary: dict, sent: float) -> dict:
    """A Firebase data message; its values can only be strings."""
    return {
        "state": summary["state"],
        "project": summary["project"],
        "where": summary["where"],
        "since": str(summary["since"]),
        **{state: str(count) for state, count in summary["counts"].items()},
        "agents": str(summary["agents"]),
        "sessions": json.dumps(summary["sessions"], separators=(",", ":")),
        "sent": str(int(sent)),
    }


class FcmSender:
    """Sends to a Firebase topic the watch app subscribes to, with a service account key."""

    def __init__(self, key_file: str, topic: str):
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(key_file, scopes=[FCM_SCOPE])
        self._http = AuthorizedSession(credentials)
        self._url = f"https://fcm.googleapis.com/v1/projects/{credentials.project_id}/messages:send"
        self._topic = topic

    def send(self, data: dict, wake: bool) -> None:
        # A data-only message reaches the app without a notification. High priority wakes a sleeping
        # watch, which costs battery, so only a push that calls for you uses it. The others wait
        # until the watch wakes anyway, and a newer push replaces one that is still waiting. They
        # outlive the keepalive, so a watch that wakes always finds one.
        android = {"priority": "HIGH" if wake else "NORMAL", "ttl": "600s" if wake else "1800s", "collapse_key": "state"}
        message = {"topic": self._topic, "data": data, "android": android}
        self._http.post(self._url, json={"message": message}, timeout=10).raise_for_status()


class LogSender:
    """Stands in for Firebase until the relay has a key: logs what it would send."""

    def send(self, data: dict, wake: bool) -> None:
        log.info("push not sent (no Firebase key): %s", data)


def headline(summary: dict | None) -> tuple:
    """What a push can't wait for: the word on the watch, and who "needs you" or "your turn" is about."""
    if summary is None:
        return ()
    return (summary["state"], summary["project"]) if summary["state"] in CALLS_YOU else (summary["state"],)


class Relay:
    """Holds the sessions and pushes when what the watch shows changes. To save the watch's battery,
    smaller changes (counts, agents, the session list) are sent together now and then. While Claude
    is busy it repeats the push now and then, so the watch can tell a current state from an old one."""

    def __init__(self, sessions, sender, keepalive_min: float = 15, batch_min: float = 2, clock=time.time):
        self._sessions = sessions
        self._sender = sender
        self._keepalive = keepalive_min * 60
        self._batch = batch_min * 60
        self._clock = clock
        self._lock = threading.Lock()  # guards the sessions
        self._send_lock = threading.Lock()  # one push at a time, without holding up the hooks
        self._last = None
        self._last_at = 0.0

    def record(self, event: dict, where: str) -> None:
        with self._lock:
            self._sessions.apply(event, where)

    def summary(self) -> dict:
        with self._lock:
            return self._sessions.summary()

    def push(self) -> None:
        with self._send_lock:
            summary = self.summary()
            now = self._clock()
            moved = headline(summary) != headline(self._last)
            batched = summary != self._last and now - self._last_at >= self._batch
            due = summary["state"] != "sleeping" and now - self._last_at >= self._keepalive
            if not (moved or batched or due):
                return
            wake = moved and summary["state"] in CALLS_YOU
            try:
                self._sender.send(to_message(summary, now), wake)
            except Exception:
                log.exception("push failed; trying again at the next change or within a minute")
                return
            self._last, self._last_at = summary, now
            log.info("pushed %s %s, %s", summary["state"], summary["project"], "waking the watch" if wake else "not waking")
