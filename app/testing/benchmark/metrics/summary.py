from app.testing.benchmark.models import LatencyStats

def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    index = round((pct / 100.0) * (len(ordered) - 1))
    return ordered[index]

def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)

def summarize_latency(values_ms: list[float]) -> LatencyStats:
    clean_values = [v for v in values_ms if v >= 0]

    if not clean_values:
        return LatencyStats()

    return LatencyStats(
        count=len(clean_values),
        p50_ms=percentile(clean_values, 50),
        p95_ms=percentile(clean_values, 95),
        mean_ms=mean(clean_values),
        min_ms=min(clean_values),
        max_ms=max(clean_values),
    )