import os
import sys
from typing import List

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

client = TestClient(main.app)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake image body"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"fake image body"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"fake image body"


@pytest.fixture
def gemini_calls(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """Replace the Gemini call so no test touches the real API. Records each call."""
    calls: List[str] = []

    def fake_call_gemini(image_bytes: bytes, mime_type: str) -> str:
        calls.append(mime_type)
        return "raw text"

    def fake_parse(raw_text: str) -> main.DetectResult:
        return main.DetectResult(
            family="Arial",
            confidence="high",
            category="sans-serif",
            alternatives=["Helvetica", "Roboto"],
            sizeMinPx=14,
            sizeMaxPx=18,
            sizeLabel="body text",
            reasoning="Test data.",
        )

    monkeypatch.setattr(main, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(main, "parse_gemini_response", fake_parse)
    return calls


def post_file(content: bytes, filename: str = "x.png", content_type: str = "image/png"):
    return client.post("/detect", files={"file": (filename, content, content_type)})


def test_rejects_non_image(gemini_calls: List[str]) -> None:
    response = post_file(b"just some text", "x.txt", "text/plain")
    assert response.status_code == 415
    assert gemini_calls == []


def test_rejects_gif(gemini_calls: List[str]) -> None:
    response = post_file(b"GIF89a" + b"0" * 20, "x.gif", "image/gif")
    assert response.status_code == 415
    assert gemini_calls == []


def test_rejects_wrong_content_type_claim(gemini_calls: List[str]) -> None:
    # Header says PNG but the bytes are not an image, so it must be rejected.
    response = post_file(b"not really a png", "x.png", "image/png")
    assert response.status_code == 415
    assert gemini_calls == []


def test_rejects_empty_file(gemini_calls: List[str]) -> None:
    response = post_file(b"")
    assert response.status_code == 400
    assert gemini_calls == []


def test_rejects_oversize_file(gemini_calls: List[str]) -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"0" * main.MAX_UPLOAD_BYTES
    response = post_file(big)
    assert response.status_code == 413
    assert gemini_calls == []


def test_rejects_missing_file(gemini_calls: List[str]) -> None:
    response = client.post("/detect")
    assert response.status_code == 422
    assert gemini_calls == []


@pytest.mark.parametrize(
    "content,mime",
    [(PNG_BYTES, "image/png"), (JPEG_BYTES, "image/jpeg"), (WEBP_BYTES, "image/webp")],
)
def test_accepts_supported_types(gemini_calls: List[str], content: bytes, mime: str) -> None:
    response = post_file(content)
    assert response.status_code == 200
    assert response.json()["family"] == "Arial"
    assert gemini_calls == [mime]
