"""Per-step latency for the RAG pipeline."""
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Deque, Dict

_WINDOW = 500
_lock = threading.Lock()
_samples: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=_WINDOW))


class StepTimer:
    """Collects the duration of named steps; a repeated step accumulates."""

    def __init__(self) -> None:
        self.steps: Dict[str, float] = {}

    @contextmanager
    def step(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            self.steps[name] = round(self.steps.get(name, 0.0) + elapsed, 2)


def record_timings(steps: Dict[str, float]) -> None:
    with _lock:
        for name, value in steps.items():
            _samples[name].append(value)


def _percentile(ordered, fraction: float) -> float:
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return round(ordered[index], 2)


def latency_snapshot() -> Dict[str, Dict[str, float]]:
    """p50/p95/last per step over the most recent requests."""
    with _lock:
        copies = {name: list(values) for name, values in _samples.items()}
    return {
        name: {
            "count": len(values),
            "p50_ms": _percentile(sorted(values), 0.5),
            "p95_ms": _percentile(sorted(values), 0.95),
            "last_ms": round(values[-1], 2),
        }
        for name, values in copies.items()
        if values
    }
