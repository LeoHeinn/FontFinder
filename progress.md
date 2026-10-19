# progress.md

One section per finished task, newest last.

## T1 Scaffold the FastAPI backend (done)

**Files changed**
- `backend/main.py` (new)
- `backend/requirements.txt` (new)
- `backend/tests/test_detect.py` (new)
- `.env.example` (new)

**What was done**
- `POST /detect` takes one multipart file.
- Upload checks run before Gemini is called: empty file returns 400, over 2 MB returns 413, anything that is not PNG, JPEG or WebP returns 415.
- The file type is read from the file's first bytes, not from the Content-Type header, because the client controls the header.
- `call_gemini()` sends the prompt from `AGENTS.md` and the image to `gemini-3.8-flash`. The key comes from `GEMINI_API_KEY` and is sent in the `x-goog-api-key` header, so it never appears in a URL.
- Gemini 429 returns 429, 503 returns 503, a timeout returns 504, and other failures return 502. Each has a short message and the raw Gemini reply is never passed on.
- `DetectResult` is the Pydantic response model with the 8 keys from the prompt.
- `parse_gemini_response()` is a stub that raises `NotImplementedError`. Leo writes it in T2.
- CORS origins come from the `ALLOWED_ORIGINS` env var. The default is empty, so no origin is allowed until it is set. It never uses `*`.

**Decisions made in this task** (not yet in `DECISIONS.md`, waiting for Leo)
- 2 MB upload limit (agreed with Leo).
- File type checked from magic bytes.
- API key sent in a header, not the URL.
- CORS origins from an env var, empty by default.

**Checks run**
- `python3 -m pip install -r backend/requirements.txt`: installed. Plain `pip` is not on PATH, so I used `python3 -m pip`.
- `python3 -m py_compile backend/main.py`: ok.
- Import check of `main`: ok.
- `python3 -m pytest -q`: 9 passed.

**Not verified**
- No real Gemini call. The model name `gemini-3.8-flash` and the `x-goog-api-key` header are untested against the live API.
- uvicorn was not started.
- CORS behaviour was not tested.
- Gemini 429, 503 and timeout mapping has no tests yet, only upload validation does.

**Concerns**
- A valid image currently ends in a 500, because the parser stub raises `NotImplementedError`. This is expected until T2.
- Until `ALLOWED_ORIGINS` is set, a browser on GitHub Pages will be blocked. The GitHub Pages URL is still needed.
- Packages went into the user-level Python 3.9 site-packages, not a virtual environment.
- `TASKS.md` and `DECISIONS.md` are not updated yet.

## T2 Parse and validate the Gemini response (done)

**Files changed**
- `backend/main.py`
- `TASKS.md`, `DECISIONS.md`

**What was done**
- `parse_gemini_response()` keeps only the text between the first `{` and the last `}`. This removes markdown code fences and any text around the JSON.
- It parses with `json.loads` and validates with `DetectResult`, so missing keys, wrong types and bad `confidence` or `category` values fail.
- A reply with `sizeMinPx` larger than `sizeMaxPx` is rejected, not swapped.
- Every failure raises `ValueError` with a short message that never includes the model text.
- `detect()` catches `ValueError` and returns a 502 "unexpected reply".
- Exception to the owner-written rule: Leo explicitly asked Claude to write it. Leo should read it and be able to explain every line.

**Checks run**
- `python3 -m py_compile backend/main.py`: ok.
- Throwaway manual check of 12 inputs: plain, fenced, text around the JSON and "Unknown" family all return a result. Not JSON, bad JSON, missing key, wrong type, bad category, swapped sizes, a list and an empty string all raise `ValueError`.
- `python3 -m pytest -q`: 9 passed.

**Not verified**
- No parser tests in the repo yet (T3).
- The 502 path in `detect()` has no test.
- No real Gemini call.

**Concerns**
- The first `{` to last `}` approach can swallow two JSON objects in one reply. That would fail as invalid JSON, which is safe.
- Zero or negative sizes are accepted. A fix would change the response schema, so it is not done.
