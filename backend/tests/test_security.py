import os
import sys
from typing import List

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake image body"
GOOD_REPLY = (
    '{"family": "Arial", "confidence": "high", "category": "sans-serif", "alternatives": ["Helvetica"],'
    ' "sizeMinPx": 14, "sizeMaxPx": 18, "sizeLabel": "body text"}'
)


@pytest.fixture
def gemini_calls(monkeypatch: pytest.MonkeyPatch) -> List[int]:
    """Replace the Gemini call with a fake that returns a valid reply and counts calls."""
    calls: List[int] = []

    def fake_call_gemini(image_bytes: bytes, mime_type: str) -> str:
        calls.append(1)
        return GOOD_REPLY

    monkeypatch.setattr(main, "call_gemini", fake_call_gemini)
    return calls


def post_png(client: TestClient):
    return client.post("/detect", files={"file": ("x.png", PNG_BYTES, "image/png")})


# Rate limiter on its own, with a fake clock


def test_limiter_blocks_the_sixth_request_from_one_client() -> None:
    limiter = main.RateLimiter(per_client=5, total=30, window_seconds=60)
    results = [limiter.allow("1.1.1.1", now=float(second)) for second in range(6)]
    assert results == [True, True, True, True, True, False]


def test_limiter_allows_again_after_the_window() -> None:
    limiter = main.RateLimiter(per_client=5, total=30, window_seconds=60)
    for second in range(5):
        assert limiter.allow("1.1.1.1", now=float(second))
    assert not limiter.allow("1.1.1.1", now=59.0)
    # The first request was at 0 s, so at 60 s it has left the window and one slot is free.
    assert limiter.allow("1.1.1.1", now=60.0)


def test_limiter_keeps_clients_apart() -> None:
    limiter = main.RateLimiter(per_client=5, total=30, window_seconds=60)
    for second in range(5):
        assert limiter.allow("1.1.1.1", now=float(second))
    assert not limiter.allow("1.1.1.1", now=5.0)
    assert limiter.allow("2.2.2.2", now=5.0)


def test_limiter_total_cap_holds_with_many_clients() -> None:
    limiter = main.RateLimiter(per_client=5, total=30, window_seconds=60)
    for number in range(30):
        assert limiter.allow("client-" + str(number), now=1.0)
    # A brand new client is still blocked, because everyone together has used the 30 slots.
    assert not limiter.allow("client-new", now=2.0)


def test_blocked_requests_do_not_use_a_slot() -> None:
    limiter = main.RateLimiter(per_client=1, total=30, window_seconds=60)
    assert limiter.allow("1.1.1.1", now=0.0)
    for second in range(1, 50):
        assert not limiter.allow("1.1.1.1", now=float(second))
    # Only the first request was recorded, so the client is free again once it leaves the window.
    assert limiter.allow("1.1.1.1", now=60.0)


def test_limiter_forgets_idle_clients() -> None:
    limiter = main.RateLimiter(per_client=5, total=30, window_seconds=60)
    limiter.allow("1.1.1.1", now=0.0)
    limiter.allow("2.2.2.2", now=0.0)
    limiter.allow("3.3.3.3", now=100.0)
    assert list(limiter.by_client) == ["3.3.3.3"]


# Rate limiter through the endpoint


def test_detect_blocks_the_sixth_request_without_calling_gemini(gemini_calls: List[int]) -> None:
    client = TestClient(main.app)
    statuses = [post_png(client).status_code for _ in range(6)]
    assert statuses == [200, 200, 200, 200, 200, 429]
    assert len(gemini_calls) == 5


def test_detect_rate_limit_message(gemini_calls: List[int]) -> None:
    client = TestClient(main.app)
    for _ in range(5):
        post_png(client)
    response = post_png(client)
    assert response.json() == {"detail": main.RATE_LIMIT_DETAIL}


def test_rejected_uploads_do_not_count(gemini_calls: List[int]) -> None:
    client = TestClient(main.app)
    for _ in range(10):
        response = client.post("/detect", files={"file": ("x.txt", b"not an image", "text/plain")})
        assert response.status_code == 415
    assert post_png(client).status_code == 200


# API docs are switched off


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_off(path: str) -> None:
    assert TestClient(main.app).get(path).status_code == 404


# CORS


def test_cors_preflight_from_unknown_origin_is_refused() -> None:
    client = TestClient(main.app)
    response = client.options(
        "/detect",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
