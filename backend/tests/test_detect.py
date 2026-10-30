import asyncio
import os
import sys
import tempfile
from typing import Any, Iterator, List, Optional, Tuple

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

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



# Upload size limit (BodySizeLimitMiddleware)


def multipart_body(content: bytes, boundary: str) -> bytes:
    """Build a multipart form body by hand, so a test can send it in chunks."""
    return (
        b"--" + boundary.encode() + b"\r\n"
        + b'Content-Disposition: form-data; name="file"; filename="x.png"\r\n'
        + b"Content-Type: image/png\r\n\r\n"
        + content
        + b"\r\n--" + boundary.encode() + b"--\r\n"
    )


def test_rejects_oversize_upload_without_content_length(gemini_calls: List[str]) -> None:
    body = multipart_body(b"\x89PNG\r\n\x1a\n" + b"0" * main.MAX_UPLOAD_BYTES, "testboundary")

    def chunks() -> Iterator[bytes]:
        for start in range(0, len(body), 64 * 1024):
            yield body[start : start + 64 * 1024]

    response = client.post(
        "/detect",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=testboundary"},
    )
    # A generator body is sent chunked, so the server gets no Content-Length to trust.
    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert gemini_calls == []


def test_image_just_under_limit_stays_in_memory(
    gemini_calls: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # rollover() is what moves a SpooledTemporaryFile from memory to disk.
    rollovers: List[int] = []
    original_rollover = tempfile.SpooledTemporaryFile.rollover

    def recording_rollover(self: Any) -> None:
        rollovers.append(1)
        original_rollover(self)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", recording_rollover)
    image = b"\x89PNG\r\n\x1a\n" + b"0" * (main.MAX_UPLOAD_BYTES - 1024)
    response = post_file(image)
    assert response.status_code == 200
    assert rollovers == []


def run_middleware(chunks: List[bytes], max_bytes: int) -> Tuple[List[bytes], int, Optional[int]]:
    """Send chunks through the middleware into an app that reads the whole body.
    Returns the chunks the app got, how many times receive() was called, and the error status if any."""
    app_chunks: List[bytes] = []
    receive_calls = 0

    async def receive() -> Message:
        nonlocal receive_calls
        index = receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": chunks[index], "more_body": index < len(chunks) - 1}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        more_body = True
        while more_body:
            message = await receive()
            app_chunks.append(message["body"])
            more_body = message.get("more_body", False)

    async def send(message: Message) -> None:
        pass

    middleware = main.BodySizeLimitMiddleware(app, max_bytes=max_bytes)
    try:
        asyncio.run(middleware({"type": "http"}, receive, send))
    except HTTPException as error:
        return app_chunks, receive_calls, error.status_code
    return app_chunks, receive_calls, None


def test_middleware_stops_reading_after_limit() -> None:
    app_chunks, receive_calls, status = run_middleware([b"x" * 400] * 5, max_bytes=1000)
    assert status == 413
    # The 3rd chunk takes the total to 1200, so it is never handed to the app and no 4th chunk is read.
    assert receive_calls == 3
    assert app_chunks == [b"x" * 400] * 2


@pytest.mark.parametrize(
    "chunks",
    [[b"x" * 300] * 3, [b"x" * 500] * 2],
    ids=["under-limit", "exactly-at-limit"],
)
def test_middleware_passes_small_body_through(chunks: List[bytes]) -> None:
    app_chunks, receive_calls, status = run_middleware(chunks, max_bytes=1000)
    assert status is None
    assert receive_calls == len(chunks)
    assert app_chunks == chunks
