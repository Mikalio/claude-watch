"""Claude Code sessions as the relay sees them, and the one state the watch shows.

Hooks report what each session does. The watch shows one state across all of them: needs you, then
working, then your turn. With none of those, the creature sleeps.

A session that started background agents ends its own turn and waits for them to report back. It
isn't your turn yet, so such a session stays "working" until its agents are done.
"""

import logging
import time
from dataclasses import dataclass, field

log = logging.getLogger("relay")

# Hook events and the session state they mean. Notification depends on its notification_type.
EVENT_STATES = {
    "SessionStart": "idle",
    "UserPromptSubmit": "working",
    "PreToolUse": "working",
    "PostToolUse": "working",
    "PostToolUseFailure": "working",
    "PermissionRequest": "needs",
    "Elicitation": "needs",
    "Stop": "done",
    "StopFailure": "done",
}
NOTIFICATION_STATES = {"permission_prompt": "needs", "idle_prompt": "done"}

# Background tasks that count as agents. A background shell can run for ever, so it doesn't.
AGENT_TASKS = {"subagent", "teammate"}

# The state the watch shows first; idle sessions don't count, so all-idle means sleeping.
SHOWN_FIRST = ("needs", "working", "done")
MAX_LISTED = 8  # keeps the push under Firebase's size limit


@dataclass
class Session:
    id: str
    project: str  # from the first event: the working folder can move during a session
    where: str
    state: str
    since: float  # when it entered this state
    seen: float  # its last hook event
    agents: set[str] = field(default_factory=set)  # background agents still running
    asker: str = ""  # the agent that made this session "needs you"; empty for the session itself


def project_name(cwd: str) -> str:
    """The folder name, from a Windows or a Linux path."""
    return cwd.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1] if cwd else ""


def next_state(session: Session, name: str, state: str | None, actor: str) -> str | None:
    """The state this event moves the session to, or None if it stays as it is."""
    if name == "SubagentStop" and session.state == "needs" and session.asker == actor:
        return "working"  # the agent that asked is gone
    if state == "done" and name != "StopFailure" and session.agents:
        return "working" if session.state != "needs" else None
    if state == "working" and session.state == "needs" and session.asker and session.asker != actor:
        return None  # one agent working on doesn't answer another agent's question
    if state == "working" and actor and session.state == "done":
        return None  # a last event from an agent that has finished; it isn't new work
    return state


class Sessions:
    def __init__(self, timeout_min: float = 60, done_fresh_min: float = 10, clock=time.time):
        self._sessions: dict[str, Session] = {}
        self._timeout = timeout_min * 60
        self._done_fresh = done_fresh_min * 60
        self._clock = clock

    def apply(self, event: dict, where: str) -> None:
        """Update a session from one hook event."""
        sid = event.get("session_id")
        name = event.get("hook_event_name")
        if not sid or not name:
            return
        if name == "SessionEnd":
            self._sessions.pop(sid, None)
            return
        if name == "Notification":
            state = NOTIFICATION_STATES.get(event.get("notification_type", ""))
        else:
            state = EVENT_STATES.get(name)
        now = self._clock()
        actor = event.get("agent_id") or ""
        session = self._sessions.get(sid)
        if session is None:
            if state is None:
                return
            session = Session(sid, project_name(event.get("cwd", "")), where, state, now, now, asker=actor)
            self._sessions[sid] = session
        before = session.state, len(session.agents)

        if name == "SubagentStart" and actor:
            session.agents.add(actor)
        elif name == "SubagentStop":
            session.agents.discard(actor)
        elif name == "Stop" and "background_tasks" in event:
            # Claude Code's own list of what is still running: it also corrects a missed event
            session.agents = {t.get("id", "") for t in event["background_tasks"] if t.get("type") in AGENT_TASKS}

        new = next_state(session, name, state, actor)
        if new is not None and new != session.state:
            session.state, session.since = new, now
            session.asker = actor if new == "needs" else ""
        session.seen = now
        session.where = where
        if (session.state, len(session.agents)) != before:
            log.info("%s %s: %s -> %s after %s, %d agents", sid[:8], session.project, before[0], session.state, name, len(session.agents))

    def summary(self) -> dict:
        """What the watch shows: the session that comes first, counts per state and the session list."""
        now = self._clock()
        for sid in [s.id for s in self._sessions.values() if now - s.seen > self._timeout]:
            del self._sessions[sid]
        listed = []
        for s in self._sessions.values():
            # "Your turn" stands out for a while; after that the session just waits, like idle
            state = "idle" if s.state == "done" and now - s.since > self._done_fresh else s.state
            listed.append({"project": s.project, "where": s.where, "state": state, "since": int(s.since), "agents": len(s.agents)})
        listed.sort(key=lambda s: (SHOWN_FIRST.index(s["state"]) if s["state"] in SHOWN_FIRST else len(SHOWN_FIRST), -s["since"]))
        top = listed[0] if listed and listed[0]["state"] in SHOWN_FIRST else None
        return {
            "state": top["state"] if top else "sleeping",
            "project": top["project"] if top else "",
            "where": top["where"] if top else "",
            "since": top["since"] if top else 0,
            "counts": {state: sum(s["state"] == state for s in listed) for state in SHOWN_FIRST},
            "agents": sum(s["agents"] for s in listed),
            "sessions": listed[:MAX_LISTED],
        }
