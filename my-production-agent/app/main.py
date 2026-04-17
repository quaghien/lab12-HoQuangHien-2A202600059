import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from openai import OpenAI
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from collections.abc import Iterator
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_and_record_budget, estimate_cost_usd
from app.rate_limiter import check_rate_limit


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
logger = logging.getLogger("agent")

redis_client = redis.from_url(settings.redis_url, decode_responses=True)
start_time = time.time()
is_shutting_down = False
openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


def log_event(event: str, **kwargs) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **kwargs,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


def _close_redis_connection() -> None:
    try:
        redis_client.close()
    except Exception as exc:  # pragma: no cover - defensive cleanup
        log_event("shutdown_redis_close_error", detail=str(exc))


def _build_messages(question: str, history: list[dict]) -> list[dict]:
    messages: list[dict] = [
        {
            "role": "system",
            "content": "You are a helpful and concise assistant.",
        }
    ]
    for item in history[-10:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages


def _iter_answer_stream(answer: str) -> Iterator[str]:
    """Stream text đã có (sau khi OpenAI trả về full answer)."""
    for word in answer.split():
        yield f"{word} "


def _generate_answer(client: OpenAI, question: str, history: list[dict]) -> tuple[str, str]:
    messages = _build_messages(question, history)
    completion = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.2,
    )
    answer = completion.choices[0].message.content or ""
    return answer.strip(), "openai"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.shutting_down = False
    app.state.shutdown_signal = None
    log_event("startup_begin", app=settings.app_name, version=settings.app_version)
    redis_client.ping()
    app.state.ready = True
    log_event("startup_ready")
    yield
    log_event("graceful_shutdown_begin")
    app.state.ready = False
    _close_redis_connection()
    log_event("shutdown_complete")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=4000)
    stream: bool = False


def _on_shutdown_signal(signum, _frame):
    global is_shutting_down
    is_shutting_down = True
    app.state.ready = False
    app.state.shutting_down = True
    app.state.shutdown_signal = signum
    log_event("shutdown_signal_received", signal=signum, action="stop_accepting_new_requests")


signal.signal(signal.SIGTERM, _on_shutdown_signal)
signal.signal(signal.SIGINT, _on_shutdown_signal)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.time()
    if getattr(app.state, "shutting_down", False) and request.url.path not in {"/health", "/ready"}:
        return JSONResponse(status_code=503, content={"detail": "Server is shutting down"})

    response = await call_next(request)
    elapsed_ms = round((time.time() - started) * 1000, 2)
    log_event(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - start_time, 2),
        "shutting_down": is_shutting_down,
    }


@app.get("/ready")
def ready():
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Not ready")
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis not ready: {exc}") from exc
    return {"status": "ready"}


@app.post("/ask")
def ask(payload: AskRequest, _auth: None = Depends(verify_api_key)):
    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI chưa cấu hình. Đặt biến môi trường OPENAI_API_KEY.",
        )

    check_rate_limit(redis_client, payload.user_id)

    history_key = f"history:{payload.user_id}"
    history_raw = redis_client.lrange(history_key, 0, -1)
    history = [json.loads(item) for item in history_raw]

    try:
        answer, provider = _generate_answer(openai_client, payload.question, history)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc
    estimated_cost = estimate_cost_usd(payload.question + " " + answer)
    check_and_record_budget(redis_client, payload.user_id, estimated_cost)

    user_message = {"role": "user", "content": payload.question}
    assistant_message = {"role": "assistant", "content": answer}
    redis_client.rpush(history_key, json.dumps(user_message), json.dumps(assistant_message))
    redis_client.ltrim(history_key, -settings.history_max_items, -1)
    redis_client.expire(history_key, 30 * 24 * 3600)

    if payload.stream:
        return StreamingResponse(_iter_answer_stream(answer), media_type="text/plain")

    return {
        "user_id": payload.user_id,
        "model": settings.llm_model,
        "provider": provider,
        "question": payload.question,
        "answer": answer,
        "history_items": len(history) + 2,
        "estimated_cost_usd": round(estimated_cost, 6),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
