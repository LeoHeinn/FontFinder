import base64
import os
from typing import List, Literal, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

MODEL = "gemini-3.8-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)
GEMINI_TIMEOUT_SECONDS = 30
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB, agreed with Leo

PROMPT = """You are a typography expert. Identify the font in this screenshot of text.
Respond with ONLY a JSON object, no markdown, with these keys:
"family" (best-match font family name, prefer well-known names),
"confidence" ("high" | "medium" | "low"),
"category" ("serif" | "sans-serif" | "monospace" | "script" | "display"),
"alternatives" (array of 2-3 similar font family names),
"sizeMinPx" (number), "sizeMaxPx" (number) - approximate rendered size of the main text in CSS px based on the image,
"sizeLabel" (e.g. "body text", "heading", "caption"),
"reasoning" (one or two sentences on the letterform features you used).
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


app = FastAPI()

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
    """Send the image to Gemini and return the raw model text. Raises HTTPException on failure."""
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

    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers={"x-goog-api-key": api_key},
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="The font service timed out. Try again.")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Could not reach the font service.")

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    if response.status_code == 503:
        raise HTTPException(status_code=503, detail="The font service is busy. Try again soon.")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="The font service returned an error.")

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="The font service returned an unexpected reply.")


def parse_gemini_response(raw_text: str) -> DetectResult:
    """Turn raw model text into a validated DetectResult. Leo writes this in T2."""
    raise NotImplementedError


@app.post("/detect", response_model=DetectResult)
def detect(file: UploadFile = File(...)) -> DetectResult:
    # Read one byte past the limit so an oversize file is detected without loading all of it.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. Maximum is 2 MB.")

    mime_type = sniff_image_type(data)
    if mime_type is None:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG and WebP images are accepted.")

    raw_text = call_gemini(data, mime_type)
    return parse_gemini_response(raw_text)
