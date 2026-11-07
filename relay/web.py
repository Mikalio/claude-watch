"""The relay's web API. Claude Code's hooks post every event here; the relay works out what the
watch should show and pushes it when it changes. Start it with
uvicorn relay.web:create_app --factory."""

import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, Response

from relay.push import FcmSender, LogSender, Relay
from relay.sessions import Sessions

log = logging.getLogger("relay")


def make_sender():
    key_file = os.environ.get("FCM_KEY_FILE", "/data/firebase-key.json")
    topic = os.environ.get("FCM_TOPIC", "")
    if os.path.exists(key_file) and topic:
        return FcmSender(key_file, topic)
    log.warning("no Firebase key at %s or no FCM_TOPIC: pushes are only logged", key_file)
    return LogSender()


def make_relay() -> Relay:
    sessions = Sessions(
        timeout_min=float(os.environ.get("SESSION_TIMEOUT_MIN", "60")),
        done_fresh_min=float(os.environ.get("DONE_FRESH_MIN", "10")),
    )
    return Relay(
        sessions,
        make_sender(),
        keepalive_min=float(os.environ.get("KEEPALIVE_MIN", "15")),
        batch_min=float(os.environ.get("BATCH_MIN", "2")),
    )


def create_app(relay: Relay | None = None, token: str | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.environ.get("RELAY_TOKEN", "") if token is None else token
    if not token:
        raise RuntimeError("Set RELAY_TOKEN: the hooks send it with every event")
    relay = relay or make_relay()

    @asynccontextmanager
    async def lifespan(app):
        async def tick():
            # Sessions go quiet, "your turn" fades and keepalives fall due without any hook
            while True:
                await asyncio.sleep(60)
                await asyncio.to_thread(relay.push)

        task = asyncio.create_task(tick())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def check(authorization: str | None) -> None:
        if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
            raise HTTPException(status_code=401)

    @app.post("/hook", status_code=204)
    async def hook(request: Request, background: BackgroundTasks, where: str = "pc",
                   authorization: str | None = Header(default=None)):
        check(authorization)
        try:
            event = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="not JSON")
        relay.record(event if isinstance(event, dict) else {}, "Cloud" if where == "cloud" else "PC")
        background.add_task(relay.push)
        # An empty answer: anything in the body would count as a decision for Claude Code
        return Response(status_code=204)

    @app.get("/state")
    def state(authorization: str | None = Header(default=None)):
        check(authorization)
        return relay.summary()

    @app.get("/health")
    def health():
        return {"ok": True}

    return app
