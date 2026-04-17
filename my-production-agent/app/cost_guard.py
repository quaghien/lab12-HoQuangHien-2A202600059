from datetime import datetime, timezone

import redis
from fastapi import HTTPException, status

from app.config import settings


def estimate_cost_usd(text: str) -> float:
    # Rough estimate cho mock model: $0.00002 mỗi token.
    # 1 token ~ 0.75 từ, làm tròn đơn giản để tránh over-engineering.
    token_count = max(1, int(len(text.split()) * 1.3))
    return token_count * 0.00002


def check_and_record_budget(r: redis.Redis, user_id: str, estimated_cost: float) -> None:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    budget_key = f"budget:{user_id}:{month_key}"

    current_spend = float(r.get(budget_key) or 0.0)
    next_spend = current_spend + estimated_cost
    if next_spend > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly budget exceeded (${settings.monthly_budget_usd})",
        )

    r.incrbyfloat(budget_key, estimated_cost)
    r.expire(budget_key, 35 * 24 * 3600)
