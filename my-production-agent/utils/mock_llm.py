import time
from typing import Iterator


def ask(question: str, history: list[dict] | None = None, model: str = "gpt-5.4-mini") -> str:
    history = history or []
    context_hint = ""
    if history:
        last_user_msgs = [m["content"] for m in history if m.get("role") == "user"][-2:]
        if last_user_msgs:
            context_hint = f" (context: {' | '.join(last_user_msgs)})"

    time.sleep(0.1)
    return f"[{model}] Mock answer cho: {question}{context_hint}"


def ask_stream(answer: str) -> Iterator[str]:
    for word in answer.split():
        yield f"{word} "
        time.sleep(0.03)
