from relay.sessions import Sessions, project_name


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


def event(name, sid="a", cwd="C:\\Users\\me\\Code\\Grocery offers", **extra):
    return {"hook_event_name": name, "session_id": sid, "cwd": cwd, **extra}


def make():
    clock = Clock()
    return Sessions(timeout_min=60, done_fresh_min=10, clock=clock), clock


def test_no_sessions_means_sleeping():
    sessions, _ = make()
    assert sessions.summary()["state"] == "sleeping"


def test_a_turn_goes_working_needs_working_done():
    sessions, _ = make()
    sessions.apply(event("UserPromptSubmit"), "PC")
    assert sessions.summary()["state"] == "working"
    sessions.apply(event("Notification", notification_type="permission_prompt"), "PC")
    assert sessions.summary()["state"] == "needs"
    sessions.apply(event("PostToolUse"), "PC")  # approved: back to work
    assert sessions.summary()["state"] == "working"
    sessions.apply(event("Stop"), "PC")
    summary = sessions.summary()
    assert (summary["state"], summary["project"], summary["where"]) == ("done", "Grocery offers", "PC")


def test_your_turn_fades_to_sleeping():
    sessions, clock = make()
    sessions.apply(event("Stop"), "PC")
    clock.now += 11 * 60
    summary = sessions.summary()
    assert summary["state"] == "sleeping"
    assert summary["sessions"][0]["state"] == "idle"


def test_a_new_session_waits_without_waking_the_creature():
    sessions, _ = make()
    sessions.apply(event("SessionStart", source="startup"), "PC")
    assert sessions.summary()["state"] == "sleeping"


def test_most_urgent_session_wins_and_counts_add_up():
    sessions, clock = make()
    sessions.apply(event("UserPromptSubmit", sid="a", cwd="/home/user/trip-planner"), "Cloud")
    sessions.apply(event("UserPromptSubmit", sid="b"), "PC")
    clock.now += 5
    sessions.apply(event("PermissionRequest", sid="c", cwd="D:/Invoice Tool"), "PC")
    summary = sessions.summary()
    assert (summary["state"], summary["project"]) == ("needs", "Invoice Tool")
    assert summary["counts"] == {"needs": 1, "done": 0, "working": 2}
    assert [s["state"] for s in summary["sessions"]] == ["needs", "working", "working"]


def test_working_shows_before_your_turn():
    sessions, clock = make()
    sessions.apply(event("UserPromptSubmit", sid="a", cwd="/home/user/trip-planner"), "Cloud")
    clock.now += 5
    sessions.apply(event("Stop", sid="b"), "PC")
    summary = sessions.summary()
    assert (summary["state"], summary["project"]) == ("working", "trip-planner")
    assert summary["counts"] == {"needs": 0, "done": 1, "working": 1}
    assert [s["state"] for s in summary["sessions"]] == ["working", "done"]


def test_session_end_and_silence_remove_a_session():
    sessions, clock = make()
    sessions.apply(event("UserPromptSubmit", sid="a"), "PC")
    sessions.apply(event("UserPromptSubmit", sid="b"), "PC")
    sessions.apply(event("SessionEnd", sid="a", reason="prompt_input_exit"), "PC")
    assert len(sessions.summary()["sessions"]) == 1
    clock.now += 61 * 60  # the PC was switched off mid-turn
    assert sessions.summary()["state"] == "sleeping"
    assert sessions.summary()["sessions"] == []


def test_idle_notification_is_your_turn_and_unknown_events_are_ignored():
    sessions, _ = make()
    sessions.apply(event("Notification", notification_type="auth_success"), "PC")
    assert sessions.summary()["sessions"] == []
    sessions.apply(event("Notification", notification_type="idle_prompt"), "PC")
    assert sessions.summary()["state"] == "done"
    sessions.apply({"hook_event_name": "Stop"}, "PC")  # no session id
    assert len(sessions.summary()["sessions"]) == 1


def agent_task(agent_id):
    return {"id": agent_id, "type": "subagent", "status": "running", "description": "a hunter"}


def start_agents(sessions, *agent_ids):
    sessions.apply(event("UserPromptSubmit"), "PC")
    for agent_id in agent_ids:
        sessions.apply(event("SubagentStart", agent_id=agent_id, agent_type="general-purpose"), "PC")


def test_a_session_waiting_for_its_agents_keeps_working():
    sessions, clock = make()
    start_agents(sessions, "x", "y")
    started = sessions.summary()["since"]
    clock.now += 5
    sessions.apply(event("Stop", background_tasks=[agent_task("x"), agent_task("y")]), "PC")
    summary = sessions.summary()
    assert (summary["state"], summary["agents"], summary["since"]) == ("working", 2, started)
    assert summary["sessions"][0]["agents"] == 2

    # One reports back: the session reads it and waits again
    sessions.apply(event("SubagentStop", agent_id="x"), "PC")
    sessions.apply(event("Stop", background_tasks=[agent_task("y")]), "PC")
    assert (sessions.summary()["state"], sessions.summary()["agents"]) == ("working", 1)

    # The last one reports back: now it's your turn
    sessions.apply(event("SubagentStop", agent_id="y"), "PC")
    assert sessions.summary()["state"] == "working"
    sessions.apply(event("Stop", background_tasks=[]), "PC")
    assert (sessions.summary()["state"], sessions.summary()["agents"]) == ("done", 0)


def test_the_stop_list_corrects_a_missed_subagent_event():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("Stop", background_tasks=[]), "PC")  # its SubagentStop never arrived
    assert (sessions.summary()["state"], sessions.summary()["agents"]) == ("done", 0)
    sessions.apply(event("UserPromptSubmit"), "PC")
    sessions.apply(event("Stop", background_tasks=[agent_task("z")]), "PC")  # nor did this SubagentStart
    assert (sessions.summary()["state"], sessions.summary()["agents"]) == ("working", 1)


def test_a_background_shell_is_not_an_agent():
    sessions, _ = make()
    sessions.apply(event("UserPromptSubmit"), "PC")
    shell = {"id": "s", "type": "shell", "status": "running", "description": "dev server", "command": "npm run dev"}
    sessions.apply(event("Stop", background_tasks=[shell]), "PC")
    assert (sessions.summary()["state"], sessions.summary()["agents"]) == ("done", 0)


def test_stop_without_a_task_list_goes_by_the_subagent_events():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("Stop"), "PC")
    assert sessions.summary()["state"] == "working"


def test_idle_notification_doesnt_end_the_wait_for_agents():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("Notification", notification_type="idle_prompt"), "PC")
    assert sessions.summary()["state"] == "working"


def test_a_failed_turn_is_your_turn_even_with_agents_running():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("StopFailure"), "PC")
    assert sessions.summary()["state"] == "done"


def test_a_late_agent_event_doesnt_undo_your_turn():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("SubagentStop", agent_id="x"), "PC")
    sessions.apply(event("Stop", background_tasks=[]), "PC")
    sessions.apply(event("PostToolUse", agent_id="x"), "PC")
    assert sessions.summary()["state"] == "done"


def test_only_the_agent_that_asked_clears_needs_you():
    sessions, _ = make()
    start_agents(sessions, "x", "y")
    sessions.apply(event("PermissionRequest", agent_id="x"), "PC")
    sessions.apply(event("Notification", notification_type="permission_prompt"), "PC")
    sessions.apply(event("PostToolUse", agent_id="y"), "PC")
    sessions.apply(event("PostToolUse"), "PC")
    sessions.apply(event("Stop", background_tasks=[agent_task("x"), agent_task("y")]), "PC")
    assert sessions.summary()["state"] == "needs"
    sessions.apply(event("PostToolUse", agent_id="x"), "PC")
    assert sessions.summary()["state"] == "working"


def test_needs_you_ends_when_the_agent_that_asked_stops():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("PermissionRequest", agent_id="x"), "PC")
    sessions.apply(event("SubagentStop", agent_id="x"), "PC")
    assert sessions.summary()["state"] == "working"


def test_the_session_asking_is_cleared_by_any_event_as_before():
    sessions, _ = make()
    start_agents(sessions, "x")
    sessions.apply(event("Notification", notification_type="permission_prompt"), "PC")
    sessions.apply(event("PostToolUse", agent_id="x"), "PC")
    assert sessions.summary()["state"] == "working"


def test_agents_count_across_sessions():
    sessions, _ = make()
    start_agents(sessions, "x", "y")
    sessions.apply(event("UserPromptSubmit", sid="b"), "PC")
    sessions.apply(event("SubagentStart", sid="b", agent_id="z"), "PC")
    assert sessions.summary()["agents"] == 3


def test_project_name_stays_when_the_working_folder_moves():
    sessions, _ = make()
    sessions.apply(event("UserPromptSubmit", cwd="C:\\Code\\Grocery offers"), "PC")
    sessions.apply(event("PostToolUse", cwd="C:\\Code\\Grocery offers\\grocery_offers\\static"), "PC")
    assert sessions.summary()["project"] == "Grocery offers"


def test_project_name_from_any_path():
    assert project_name("C:\\Users\\me\\Desktop\\Code programs\\Wristling") == "Wristling"
    assert project_name("/home/user/repo/") == "repo"
    assert project_name("") == ""
