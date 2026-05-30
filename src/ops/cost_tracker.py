"""LLM cost tracking — per-model pricing and usage estimation."""

MODEL_PRICING = {
    "deepseek-chat": {"input": 0.27, "output": 1.10},     # per 1M tokens
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given token usage."""
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 5.0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def record_usage(model: str, input_tokens: int, output_tokens: int,
                 latency_ms: int = 0):
    """Record model usage to SQLite for tracking."""
    try:
        from src.store.db import ReviewRepo
        db = ReviewRepo()
        try:
            cost = estimate_cost(model, input_tokens, output_tokens)
            db._conn.execute(
                "INSERT INTO model_usages (review_run_id, model, provider, call_count, total_tokens, total_latency_ms, cost_estimate) VALUES (?,?,?,?,?,?,?)",
                (0, model, model.split("-")[0], 1, input_tokens + output_tokens, latency_ms, cost),
            )
            db._conn.commit()
        finally:
            db.close()
    except Exception:
        pass


def get_cost_summary(repo: str = "", days: int = 30) -> dict:
    """Get cost summary from SQLite."""
    try:
        from src.store.db import ReviewRepo
        db = ReviewRepo()
        try:
            rows = db._conn.execute(
                "SELECT model, SUM(call_count) as calls, SUM(total_tokens) as tokens, SUM(cost_estimate) as cost FROM model_usages GROUP BY model"
            ).fetchall()
            return {
                "models": [{"model": r["model"], "calls": r["calls"], "tokens": r["tokens"], "cost": round(r["cost"], 4)} for r in rows],
            }
        finally:
            db.close()
    except Exception:
        return {"models": []}
