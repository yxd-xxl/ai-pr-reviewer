"""Robust confidence parsing — handles both int (0-100) and float (0-1)."""


def parse_confidence(raw) -> float:
    """Parse LLM confidence output. Always returns 0.0-1.0."""
    try:
        val = float(raw)
    except (ValueError, TypeError):
        return 0.25
    if val > 1.0:
        return val / 100.0
    return val


def normalize_threshold(threshold: float) -> float:
    """Ensure threshold is in 0-1 range for internal comparisons."""
    if threshold > 1.0:
        return threshold / 100.0
    return threshold
