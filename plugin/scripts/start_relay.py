"""Starts the Wristling relay on this PC, if it isn't running: python start_relay.py [--stop]

Claude Code runs this when a session starts, through the plugin's SessionStart hook. It only does something after
python -m wristling setup has put the relay on this PC. It uses only the standard library, since the relay itself
runs in its own environment in ~/.wristling, and it prints nothing, since what a SessionStart hook prints goes to Claude.
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("WRISTLING_HOME") or Path.home() / ".wristling")
FOLDER = HOME / "pc"
PID_FILE = FOLDER / "relay.pid"
PORT = 8079
STARTING_S = 20  # how long a relay that was just started gets before another one is tried


def running() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1):
            return True
    except (OSError, urllib.error.URLError):
        return False


def just_started() -> bool:
    try:
        return time.time() - PID_FILE.stat().st_mtime < STARTING_S
    except OSError:
        return False


def start() -> None:
    try:
        state = json.loads((HOME / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    python = HOME / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if state.get("relay_where") != "pc" or not python.exists() or running() or just_started():
        return
    env = {**os.environ, "RELAY_TOKEN": state["token"], "FCM_TOPIC": state["topic"], "PYTHONUNBUFFERED": "1",
           "PYTHONDONTWRITEBYTECODE": "1", "FCM_KEY_FILE": str(HOME / "firebase-key.json")}
    if state.get("push_key"):
        env["PUSH_KEY"] = state["push_key"]
    # On its own, so it outlives the session that started it
    alone = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
             if os.name == "nt" else {"start_new_session": True})
    with (FOLDER / "relay.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(python), "-m", "uvicorn", "relay.web:create_app", "--factory", "--host", "127.0.0.1", "--port", str(PORT),
             "--no-access-log"],
            cwd=FOLDER, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **alone)
    PID_FILE.write_text(str(process.pid), encoding="utf-8")


def stop() -> None:
    try:
        os.kill(int(PID_FILE.read_text(encoding="utf-8")), signal.SIGTERM)
    except (OSError, ValueError):
        pass
    PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    stop() if "--stop" in sys.argv else start()
