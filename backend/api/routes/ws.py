"""WebSocket notifications (Redis Pub/Sub fan-out)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Final

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.config import get_settings
from backend.logging_config import get_logger
from backend.services.auth import _claims_from_payload, _decode_jwt
from backend.services.notifications import channel_for_user, get_redis

router: Final[APIRouter] = APIRouter(tags=["websocket"])
log = get_logger(__name__)

# Short poll so uvicorn reload / shutdown can cancel this handler promptly. Using
# ``pubsub.listen()`` blocks inside Redis with no timeout, which can stall reload.
_PUBSUB_POLL_TIMEOUT_S: Final[float] = 1.0


@router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    settings = get_settings()
    try:
        payload = _decode_jwt(token, settings)
        claims = _claims_from_payload(payload)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    user_id = str(claims.user_id)
    channel = channel_for_user(user_id)
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    log.info("ws.notifications.subscribed", user_id=user_id, channel=channel)

    async def _heartbeat() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping", "ts": time.time()})
            except Exception:
                break

    hb = asyncio.create_task(_heartbeat())
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=_PUBSUB_POLL_TIMEOUT_S,
            )
            if message is None:
                continue
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, str):
                try:
                    await websocket.send_text(data)
                except Exception:
                    break
            elif isinstance(data, bytes):
                await websocket.send_text(data.decode("utf-8", errors="replace"))
    except WebSocketDisconnect:
        log.info("ws.notifications.disconnect", user_id=user_id)
    finally:
        hb.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await hb
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            log.warning("ws.notifications.cleanup_failed", user_id=user_id, exc_info=True)


__all__ = ["router"]
