import base64
import json
import logging
import os
from typing import List, Literal, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

load_dotenv()

# Tried in order, as (model name, timeout in seconds). The next model is used only when
# one is busy, rate limited, slow or broken. Timeouts add up to 80 s, under the 90 s the frontend waits.
MODELS = [
    ("gemini-3-flash-preview", 40),
    ("gemini-3.5-flash-lite", 20),
    ("gemini-3.1-flash-lite", 20),
]
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"

# uvicorn prints this logger's INFO lines. Only model names and status codes are logged, never images or the key.
logger = logging.getLogger("uvicorn.error")
# 1 MiB. Starlette keeps uploads in memory up to 1 MiB and only then writes them
# to a temp file, so staying at or under this limit keeps images off disk.
MAX_UPLOAD_BYTES = 1024 * 1024
TOO_LARGE_DETAIL = "File is too large. Maximum is 1 MB."

PROMPT = """You are a typography expert. Identify the font in this screenshot of text.
Before deciding, study the distinctive letterforms: the shapes of a, g, R, Q, t, y and the digits, the terminals, the x-height, the stroke contrast and the spacing.
Consider the full range of fonts, including Google Fonts and modern UI and coding fonts, not only classic or system fonts. Do not answer Helvetica, Arial or Times unless the letterforms really match them.
Respond with ONLY a JSON object, no markdown, with these keys:
"family" (best-match font family name),
"confidence" ("high" | "medium" | "low"), use "high" only when distinctive letterforms clearly match one family, otherwise "medium" or "low",
"category" ("serif" | "sans-serif" | "monospace" | "script" | "display"),
"alternatives" (array of 2-3 other font family names that could also match),
"sizeMinPx" (number), "sizeMaxPx" (number) - approximate rendered size of the main text in CSS px based on the image,
"sizeLabel" (e.g. "body text", "heading", "caption"),
"reasoning" (one or two sentences naming the letterforms that set this font apart from the alternatives).
If there is no readable text, set family to "Unknown" and confidence to "low"."""


class DetectResult(BaseModel):
    family: str
    confidence: Literal["high", "medium", "low"]
    category: Literal["serif", "sans-serif", "monospace", "script", "display"]
    alternatives: List[str]
    sizeMinPx: float
    sizeMaxPx: float
    sizeLabel: str
    reasoning: str


class BodySizeLimitMiddleware:
    """Stop reading a request once its body passes max_bytes, so big uploads are never fully received."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                # Raise before returning the chunk, so the upload parser never sees more than max_bytes.
                # FastAPI turns an HTTPException raised while reading the body into a normal response.
                if received > self.max_bytes:
                    raise HTTPException(status_code=413, detail=TOO_LARGE_DETAIL)
            return message

        await self.app(scope, limited_receive, send)


app = FastAPI()

# Counts body bytes instead of trusting Content-Length, because chunked uploads have no length.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_UPLOAD_BYTES)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST"],
    allow_headers=["*"],
)


def sniff_image_type(data: bytes) -> Optional[str]:
    """Return the MIME type from the file's first bytes, or None if not PNG/JPEG/WebP."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def call_gemini(image_bytes: bytes, mime_type: str) -> str:
    """Send the image to Gemini and return the raw model text. Tries each model in MODELS in turn.
    Raises HTTPException on failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server is missing its API key.")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ]
    }

    # If every model fails, the user gets the error from the last one.
    last_error = HTTPException(status_code=502, detail="Could not reach the font service.")

    for model, timeout in MODELS:
        try:
            response = requests.post(
                GEMINI_BASE_URL + model + ":generateContent",
                json=payload,
                headers={"x-goog-api-key": api_key},
                timeout=timeout,
            )
        except requests.Timeout:
            logger.info("%s: timed out after %s s, trying next model", model, timeout)
            last_error = HTTPException(status_code=504, detail="The font service timed out. Try again.")
            continue
        except requests.RequestException:
            # A network problem hits every model the same way, so stop here.
            raise HTTPException(status_code=502, detail="Could not reach the font service.")

        if response.status_code == 429:
            logger.info("%s: 429 rate limited, trying next model", model)
            last_error = HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
            continue
        if response.status_code == 503:
            logger.info("%s: 503 busy, trying next model", model)
            last_error = HTTPException(status_code=503, detail="The font service is busy. Try again soon.")
            continue
        if response.status_code >= 500:
            logger.info("%s: %s server error, trying next model", model, response.status_code)
            last_error = HTTPException(status_code=502, detail="The font service returned an error.")
            continue
        if response.status_code != 200:
            # 400, 401, 403, 404: our request or key is the problem, and every model would refuse it.
            logger.info("%s: %s, not trying other models", model, response.status_code)
            raise HTTPException(status_code=502, detail="The font service returned an error.")

        logger.info("%s: answered", model)
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(status_code=502, detail="The font service returned an unexpected reply.")

    raise last_error


def parse_gemini_response(raw_text: str) -> DetectResult:
    """Turn raw model text into a validated DetectResult. Raises ValueError if the text is not valid."""
    # Gemini can wrap the JSON in code fences or add text around it,
    # so keep only what is between the first "{" and the last "}".
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("Model reply contains no JSON object.")

    try:
        data = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        raise ValueError("Model reply is not valid JSON.")

    # Pydantic rejects missing keys, wrong types and values outside the allowed lists.
    try:
        result = DetectResult(**data)
    except ValidationError:
        raise ValueError("Model reply has missing keys or wrong types.")

    if result.sizeMinPx > result.sizeMaxPx:
        raise ValueError("Model reply has sizeMinPx larger than sizeMaxPx.")
    if not result.family.strip():
        raise ValueError("Model reply has an empty family.")
    return result


@app.post("/detect", response_model=DetectResult)
def detect(file: UploadFile = File(...)) -> DetectResult:
    # BodySizeLimitMiddleware has already capped the request at MAX_UPLOAD_BYTES.
    # Reading one byte past the limit keeps the check below as a backstop if the middleware is removed.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=TOO_LARGE_DETAIL)

    mime_type = sniff_image_type(data)
    if mime_type is None:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP images are accepted.")

    raw_text = call_gemini(data, mime_type)
    try:
        return parse_gemini_response(raw_text)
    except ValueError:
        raise HTTPException(status_code=502, detail="The font service returned an unexpected reply.")
