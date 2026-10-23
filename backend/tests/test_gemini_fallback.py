import os
import sys
from typing import Any, Dict, List, Tuple, Union

import pytest
import requests
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

GOOD_BODY = {"candidates": [{"content": {"parts": [{"text": "model reply"}]}}]}

# One scripted result per Gemini call: a status code, or an exception that requests.post raises.
Step = Union[int, Exception]


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return GOOD_BODY


def fake_gemini(monkeypatch: pytest.MonkeyPatch, steps: List[Step]) -> List[Tuple[str, int]]:
    """Replace requests.post with a fake that plays back steps in order.
    Returns the list of (model, timeout) for each call, so tests can check the order."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls: List[Tuple[str, int]] = []

    def fake_post(url: str, json: Dict[str, Any], headers: Dict[str, str], timeout: int) -> FakeResponse:
        model = url[len(main.GEMINI_BASE_URL) :].split(":")[0]
        calls.append((model, timeout))
        step = steps[len(calls) - 1]
        if isinstance(step, Exception):
            raise step
        return FakeResponse(step)

    monkeypatch.setattr(main.requests, "post", fake_post)
    return calls


FIRST = ("gemini-3-flash-preview", 40)
SECOND = ("gemini-3.5-flash-lite", 20)
THIRD = ("gemini-3.1-flash-lite", 20)


def test_first_model_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_gemini(monkeypatch, [200])
    assert main.call_gemini(b"img", "image/png") == "model reply"
    assert calls == [FIRST]


@pytest.mark.parametrize(
    "failure",
    [503, 429, 500, requests.Timeout()],
    ids=["busy-503", "rate-limit-429", "server-error-500", "timeout"],
)
def test_falls_back_to_next_model(monkeypatch: pytest.MonkeyPatch, failure: Step) -> None:
    calls = fake_gemini(monkeypatch, [failure, 200])
    assert main.call_gemini(b"img", "image/png") == "model reply"
    assert calls == [FIRST, SECOND]


def test_third_model_answers_after_two_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_gemini(monkeypatch, [503, requests.Timeout(), 200])
    assert main.call_gemini(b"img", "image/png") == "model reply"
    assert calls == [FIRST, SECOND, THIRD]


@pytest.mark.parametrize(
    "steps,status",
    [
        ([503, 503, 503], 503),
        ([503, requests.Timeout(), 429], 429),
        ([429, 503, requests.Timeout()], 504),
        ([503, 503, 500], 502),
    ],
    ids=["all-busy", "last-rate-limited", "last-timed-out", "last-server-error"],
)
def test_all_models_fail_returns_last_error(
    monkeypatch: pytest.MonkeyPatch, steps: List[Step], status: int
) -> None:
    calls = fake_gemini(monkeypatch, steps)
    with pytest.raises(HTTPException) as error:
        main.call_gemini(b"img", "image/png")
    assert error.value.status_code == status
    assert calls == [FIRST, SECOND, THIRD]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_do_not_fall_back(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    calls = fake_gemini(monkeypatch, [status])
    with pytest.raises(HTTPException) as error:
        main.call_gemini(b"img", "image/png")
    assert error.value.status_code == 502
    assert calls == [FIRST]


def test_network_error_does_not_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_gemini(monkeypatch, [requests.ConnectionError()])
    with pytest.raises(HTTPException) as error:
        main.call_gemini(b"img", "image/png")
    assert error.value.status_code == 502
    assert calls == [FIRST]


def test_missing_key_makes_no_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_gemini(monkeypatch, [200])
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(HTTPException) as error:
        main.call_gemini(b"img", "image/png")
    assert error.value.status_code == 500
    assert calls == []


def test_timeouts_fit_under_frontend_wait() -> None:
    # index.html gives up after 90 s, so all models together must finish before that.
    assert sum(timeout for _, timeout in main.MODELS) < 90
