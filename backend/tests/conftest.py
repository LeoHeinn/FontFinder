import os
import sys
from typing import Iterator

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Give every test its own empty rate limiter, so requests from one test never block another."""
    monkeypatch.setattr(
        main,
        "rate_limiter",
        main.RateLimiter(main.RATE_LIMIT_PER_CLIENT, main.RATE_LIMIT_TOTAL, main.RATE_LIMIT_WINDOW_SECONDS),
    )
    yield
