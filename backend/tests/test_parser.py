import json
import os
import sys
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

KEYS = [
    "family",
    "confidence",
    "category",
    "alternatives",
    "sizeMinPx",
    "sizeMaxPx",
    "sizeLabel",
]


def valid_reply() -> Dict[str, Any]:
    """A reply that should pass. Each test copies it and changes one thing."""
    return {
        "family": "Arial",
        "confidence": "high",
        "category": "sans-serif",
        "alternatives": ["Helvetica", "Roboto"],
        "sizeMinPx": 14,
        "sizeMaxPx": 18,
        "sizeLabel": "body text",
    }


def to_text(reply: Any) -> str:
    return json.dumps(reply)


# Replies that should parse


def test_plain_json_returns_every_field() -> None:
    result = main.parse_gemini_response(to_text(valid_reply()))
    assert result.family == "Arial"
    assert result.confidence == "high"
    assert result.category == "sans-serif"
    assert result.alternatives == ["Helvetica", "Roboto"]
    assert result.sizeMinPx == 14
    assert result.sizeMaxPx == 18
    assert result.sizeLabel == "body text"


def test_json_fence_is_stripped() -> None:
    text = "```json\n" + to_text(valid_reply()) + "\n```"
    assert main.parse_gemini_response(text).family == "Arial"


def test_plain_fence_is_stripped() -> None:
    text = "```\n" + to_text(valid_reply()) + "\n```"
    assert main.parse_gemini_response(text).family == "Arial"


def test_text_around_json_is_ignored() -> None:
    text = "Here is the result:\n" + to_text(valid_reply()) + "\nHope this helps."
    assert main.parse_gemini_response(text).family == "Arial"


def test_unknown_family_is_valid() -> None:
    reply = valid_reply()
    reply["family"] = "Unknown"
    reply["confidence"] = "low"
    result = main.parse_gemini_response(to_text(reply))
    assert result.family == "Unknown"
    assert result.confidence == "low"


def test_equal_min_and_max_size_is_valid() -> None:
    reply = valid_reply()
    reply["sizeMinPx"] = 16
    reply["sizeMaxPx"] = 16
    result = main.parse_gemini_response(to_text(reply))
    assert result.sizeMinPx == result.sizeMaxPx == 16


def test_reasoning_from_the_model_is_dropped() -> None:
    reply = valid_reply()
    reply["reasoning"] = "C" * 2000
    result = main.parse_gemini_response(to_text(reply))
    assert "reasoning" not in result.model_dump()


def test_extra_key_is_ignored() -> None:
    reply = valid_reply()
    reply["weight"] = "bold"
    assert main.parse_gemini_response(to_text(reply)).family == "Arial"


# Replies that should raise ValueError


@pytest.mark.parametrize(
    "text",
    ["I cannot identify this font.", "", "   \n  ", "{family: Arial}", "[1, 2, 3]"],
    ids=["prose", "empty", "whitespace", "broken-json", "json-list"],
)
def test_not_a_json_object_raises(text: str) -> None:
    with pytest.raises(ValueError):
        main.parse_gemini_response(text)


@pytest.mark.parametrize("key", KEYS)
def test_missing_key_raises(key: str) -> None:
    reply = valid_reply()
    del reply[key]
    with pytest.raises(ValueError):
        main.parse_gemini_response(to_text(reply))


@pytest.mark.parametrize(
    "key,bad_value",
    [
        ("alternatives", "Helvetica"),
        ("sizeMinPx", "big"),
        ("confidence", "very high"),
        ("category", "fancy"),
    ],
)
def test_wrong_type_or_value_raises(key: str, bad_value: Any) -> None:
    reply = valid_reply()
    reply[key] = bad_value
    with pytest.raises(ValueError):
        main.parse_gemini_response(to_text(reply))


def test_min_larger_than_max_raises() -> None:
    reply = valid_reply()
    reply["sizeMinPx"] = 20
    reply["sizeMaxPx"] = 12
    with pytest.raises(ValueError):
        main.parse_gemini_response(to_text(reply))


@pytest.mark.parametrize("family", ["", "   "], ids=["empty", "whitespace"])
def test_empty_family_raises(family: str) -> None:
    reply = valid_reply()
    reply["family"] = family
    with pytest.raises(ValueError):
        main.parse_gemini_response(to_text(reply))


@pytest.mark.parametrize(
    "text",
    [
        "MARKER-1234 is not JSON",
        '{"family": "MARKER-1234"}',
    ],
    ids=["non-json", "missing-keys"],
)
def test_error_message_does_not_contain_model_text(text: str) -> None:
    with pytest.raises(ValueError) as error:
        main.parse_gemini_response(text)
    assert "MARKER-1234" not in str(error.value)


@pytest.mark.parametrize(
    "key,bad_value",
    [
        ("family", "A" * 101),
        ("sizeLabel", "B" * 101),
        ("alternatives", ["One", "Two", "Three", "Four", "Five", "Six"]),
        ("alternatives", ["Fine", "D" * 101]),
        ("sizeMinPx", -1),
        ("sizeMaxPx", 1001),
    ],
    ids=[
        "family-too-long",
        "size-label-too-long",
        "six-alternatives",
        "alternative-too-long",
        "negative-size",
        "size-over-1000",
    ],
)
def test_answer_outside_limits_raises(key: str, bad_value: Any) -> None:
    reply = valid_reply()
    reply[key] = bad_value
    with pytest.raises(ValueError):
        main.parse_gemini_response(to_text(reply))


def test_answer_at_the_limits_is_valid() -> None:
    reply = valid_reply()
    reply["family"] = "A" * 100
    reply["alternatives"] = ["One", "Two", "Three", "Four", "Five"]
    reply["sizeMinPx"] = 0
    reply["sizeMaxPx"] = 1000
    assert main.parse_gemini_response(to_text(reply)).family == "A" * 100


# Endpoint behaviour when the parser fails


def test_detect_returns_502_when_reply_is_bad(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_gemini(image_bytes: bytes, mime_type: str) -> str:
        return "MARKER-1234 is not JSON"

    monkeypatch.setattr(main, "call_gemini", fake_call_gemini)
    client = TestClient(main.app)
    png = b"\x89PNG\r\n\x1a\n" + b"fake image body"
    response = client.post("/detect", files={"file": ("x.png", png, "image/png")})
    assert response.status_code == 502
    assert "MARKER-1234" not in response.text
