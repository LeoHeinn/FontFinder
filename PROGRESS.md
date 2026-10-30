# PROGRESS.md

Work log for Font Finder: what each task built, how it was checked, and what was still open at the end of it. Tasks are listed by ID.

## Summary

| Task | Delivered | Tests passing | Main commit |
|---|---|---|---|
| T1 | FastAPI backend: `POST /detect`, upload checks, Gemini call, error mapping, CORS | 9 | `b5a4b26` |
| T2 | `parse_gemini_response()`: JSON extraction and Pydantic validation | 9 | `a4359a9` |
| T3 | Parser tests, empty `family` rejected | 39 | `2e5afde` |
| T3b | 1 MiB upload limit enforced by counting body bytes | 44 | `6b22f2d` |
| T4 | Real image check, 60 s timeout, rewritten prompt | 44 | `4b9b9f0` |
| T4b | Fallback across three Gemini models | 61 | `e4e0f57` |
| T5 | `index.html` frontend | 44 | `d665250` |
| T5b | Layout revamp: category first, paste and drag and drop, progress, reset, dark mode | 61 | `407b08c` |
| T5c | Font name and alternatives link to a Google Fonts search | 61 | `835e421` |
| T6a | Rate limit, API docs off, answer limits, CORS tightened | 82 | `507d3e9`, `8702867` |
| T7 | README rewrite with screenshots, `reasoning` dropped from the API, docs cleaned up | 81 | `3459d3d`, `42b70d9` |

## Accuracy so far

Real results on 5 sample images whose true font is known (each one a clear example of its category).

| | Category right | Family right |
|---|---|---|
| Old prompt, `gemini-3.8-flash` (T4) | 4 of 5 | 1 of 5 |
| New prompt, `gemini-3.8-flash`, manual runs (T4) | 3 of 3 | 1 of 3 |
| New prompt, model fallback (T4b) | 4 of 5 | 2 of 5 |
| **Total** | **11 of 13** | **4 of 13** |

- Every answer had confidence "high", including the wrong ones, so confidence is not a useful signal.
- The only category miss was Bungee answered as "sans-serif" (display and sans-serif overlap).
- Small sample of clean images. Real screenshots are likely harder, and size accuracy is not measured (true sizes unknown).

---

## T1 Scaffold the FastAPI backend

**Goal:** a backend that keeps the Gemini key off the browser.
**Files:** `backend/main.py`, `backend/requirements.txt`, `backend/tests/test_detect.py`, `.env.example` (all new).

**Changes**
- `POST /detect` takes one multipart file. Before Gemini is called: empty file 400, over 2 MB 413, not PNG/JPEG/WebP 415. The type is read from the file's first bytes, not the Content-Type header, which the client controls.
- `call_gemini()` sends the prompt and image to `gemini-3.8-flash`. The key comes from `GEMINI_API_KEY` and goes in the `x-goog-api-key` header, never in a URL.
- Gemini 429 returns 429, 503 returns 503, a timeout 504, anything else 502, each with a short message. The raw Gemini reply is never passed on.
- `DetectResult` is the Pydantic response model with the 8 keys from the prompt. `parse_gemini_response()` is a stub until T2.
- CORS origins come from `ALLOWED_ORIGINS`, empty by default, never `*`.

**Checks:** install, `py_compile` and an import check ok. `pytest`: 9 passed.

**Open points**
- No real Gemini call or uvicorn run (settled in T4). CORS untested (checked locally in T5 and T6a). Gemini error mapping untested (tests in T4b).
- `ALLOWED_ORIGINS` needs the GitHub Pages URL (T6).
- Packages went into the user-level Python 3.9 site-packages, not a virtual environment.

## T2 Parse and validate the Gemini response

**Goal:** turn raw model text into a validated result.
**Files:** `backend/main.py`.

**Changes**
- Keeps only the text between the first `{` and the last `}`, which removes code fences and text around the JSON. Then `json.loads` and validation with `DetectResult`.
- A reply with `sizeMinPx` larger than `sizeMaxPx` is rejected, not swapped.
- Every failure raises `ValueError` with a short message that never includes the model text. `detect()` turns it into 502.

**Checks:** 12 manual inputs behaved as expected (plain, fenced and "Unknown" pass; bad JSON, missing key, wrong type, swapped sizes fail). `pytest`: 9 passed.

**Open points**
- No parser tests yet (added in T3).
- Two JSON objects in one reply fail as invalid JSON, which is safe.
- Zero or negative sizes accepted (limited to 0 to 1000 px in T6a).

## T3 Tests for the parser

**Goal:** lock the parser's behaviour down with tests.
**Files:** `backend/tests/test_parser.py` (new), `backend/main.py`.

**Changes**
- 28 tests call `parse_gemini_response()` directly: valid replies (plain, fenced, text around, "Unknown", equal sizes, extra key) and invalid ones (prose, empty, broken JSON, a list, each key missing, wrong types and values, min above max). The error message never contains the model text, and `/detect` returns 502 on a bad reply.
- Follow-up: an empty or whitespace-only `family` is rejected (502 instead of a blank name).
- Decision: numeric strings for sizes such as `"14"` stay accepted, since Pydantic turns them into numbers.

**Checks:** `pytest`: 37 passed, then 39 after the follow-up.

## T3b Upload size limit fix

**Goal:** make the upload limit real and keep uploads off the disk. Details in `ISSUES.md`.
**Files:** `backend/main.py`, `backend/tests/test_detect.py`.

**Changes**
- `MAX_UPLOAD_BYTES` lowered from 2 MB to 1 MiB.
- `BodySizeLimitMiddleware` counts request body bytes and raises 413 before the chunk that passes the limit reaches the upload parser. So the image stays under Starlette's 1 MiB in-memory limit and never reaches disk. It also works for chunked uploads without `Content-Length`.
- The size check in `detect()` stays as a backstop.

**Checks:** `pytest`: 44 passed (5 new). Without the middleware, a 1.5 MiB upload rolls over to disk and a just-under-1 MiB one does not, so the in-memory test can really fail.

**Open points**
- Chunk-by-chunk counting is proven by a direct middleware test, not end to end (TestClient joins chunks).
- Behaviour behind Render's proxy is unknown (T6).

## T4 Real image check

**Goal:** run `/detect` on real images and decide whether the prompt needs a line for stylized lettering.
**Files:** `backend/main.py` (timeout and prompt).

**First runs (2026-10-20):** all 5 samples failed: Inter 504, Playfair Display 503, JetBrains Mono 504, Dancing Script 503, Bungee 504. A 45 s timeout on Inter gave 503 after about 3 s and was reverted. The error mapping worked (clean 503 and 504, no traceback). T4 was paused and T5 was done in the meantime.

**Results with the old prompt (2026-10-21 and 2026-10-22)**

| Image | True font | Answer | Family right | Category right | Confidence |
|---|---|---|---|---|---|
| Inter | Inter | Helvetica | no (close) | yes | high |
| JetBrains Mono | JetBrains Mono | Letter Gothic | no | yes | high |
| Bungee, run 1 | Bungee | Bungee | yes | yes | high |
| Bungee, run 2 (via `index.html`) | Bungee | Russo One | no | no (sans-serif) | high |
| Dancing Script | Dancing Script | Snell Roundhand | no | yes | high |
| Playfair Display | Playfair Display | no answer (503 and 504 only) | | | |

Every wrong answer was a classic or system font. Successful calls took 15 to 30 s (Bungee once 29.6 s), and several calls timed out at exactly 30 s.

**Timeout:** raised from 30 to 60 s. Dancing Script then answered in 15.3 s, which would also pass at 30 s, so this does not prove 60 s helps. Kept as a margin under the page's 90 s. Replaced by per-model timeouts in T4b.

**Prompt:** removed "prefer well-known names", added a letterform checklist, put Google Fonts and modern UI and coding fonts in scope, limited "high" confidence to clear matches, and asked the reasoning to separate the pick from the alternatives. Same 8 keys, so the parser is untouched. Sample font names were left out on purpose.

**Results with the new prompt** (manual runs through `index.html`, 503 retried by hand; a first scripted run stopped after two 503s, 9.1 s and 2.4 s)

| Image | Answer | Family right | Category right | Confidence | Tries |
|---|---|---|---|---|---|
| Playfair Display | Playfair Display | yes | yes | high | 2 (503, then 200) |
| JetBrains Mono | OCR-B | no | yes | high | 3 (503, 503, then 200) |
| not recorded | wrong family | no | yes | not recorded | 2 (503, then 200) |

**Findings**
- Category right 7 of 8 across both prompts, family 2 of 8. This led to T5b (category first, family as a best guess).
- No stylized-lettering line is needed: Bungee and Dancing Script got the right category without one.
- The new confidence rule did not work ("high" on a wrong answer).
- Gemini often returned 503 on the first 1 or 2 tries. Testing rule at the time: retry at least 3 times on 503. Dropped after T4b, which gave no 503.

**Checks:** `pytest`: 44 passed. The full 5-image comparison for the new prompt moved to T4b, because the model changed there.

## T4b Gemini model fallback

**Goal:** keep requests working when one Gemini model is busy or slow.
**Files:** `backend/main.py`, `backend/tests/test_gemini_fallback.py` (new).

**Changes**
- One list `MODELS` of (name, timeout): `gemini-3-flash-preview` 40 s, `gemini-3.5-flash-lite` 20 s, `gemini-3.1-flash-lite` 20 s. Total 80 s, under the page's 90 s.
- A 503, 429, timeout or other 5xx moves on to the next model. A 400, 401, 403, 404 or network error stops at once with 502. If all three fail, the user gets the last error.
- One log line per attempt (model name and status only, never the image or the key).

**Checks:** `pytest`: 61 passed (17 new, with a fake `requests.post`: model order and timeouts, each fallback reason, last error, no fallback on client errors, no call without a key). Real run (2026-10-23):

| Image | Answer | Family right | Category right | Confidence | Model that answered | Time |
|---|---|---|---|---|---|---|
| Inter | Inter | yes | yes | high | `gemini-3.5-flash-lite` (first model timed out at 40 s) | 41.5 s |
| Playfair Display | Playfair Display | yes | yes | high | `gemini-3-flash-preview` | 6.6 s |
| JetBrains Mono | DM Mono | no | yes | high | `gemini-3-flash-preview` | 14.8 s |
| Dancing Script | Great Vibes | no | yes | high | `gemini-3-flash-preview` | 5.2 s |
| Bungee | Russo One (Bungee in alternatives) | no | no (sans-serif) | high | `gemini-3-flash-preview` | 13.6 s |

Family 2 of 5, category 4 of 5. No 503 at all, and calls were faster (5 to 15 s on the first model, against 15 to 30 s before). The fallback was used for real once (Inter).

**Open points**
- One run only: fewer 503s may be the new model or a quiet day.
- The fallback tests were not checked by breaking the code on purpose.
- A slow first model costs 40 s before the backup starts.

## T5 Write `index.html`

**Goal:** one static page that uploads a screenshot and shows the result.
**Files:** `index.html` (new, repo root).

**Changes**
- Vanilla JS: file input with preview, "Find font" button, result card, privacy note.
- Wrong types and files over 1 MiB are rejected before upload.
- `fetch` to `API_URL + "/detect"`, a loading message for the cold start, a 90 s timeout, and the backend's `detail` text on errors. Backend text goes in with `textContent`, so no HTML from the reply is parsed.
- `API_URL` is `http://127.0.0.1:8000` until T6.

**Checks:** a copy served from a temporary folder (not the repo root, which would expose `.env`) with a stubbed `fetch`: type and size checks, loading state, result card, `<b>` shown as text, 503/413/500/network error messages. `pytest`: 44 passed.

**Open points**
- The 90 s timeout message has never been triggered.
- CORS from the real GitHub Pages origin (T6).

## T5b Layout revamp

**Goal:** lead with what the model gets right (the category) and make the page easier to use.
**Files:** `index.html` (175 to 328 lines).

**Changes**
- The card leads with the category, then "Best guess: <family>" and "Could also be: <alternatives>". Confidence and size stay.
- Removed the "Why" field (the backend still sent `reasoning` until T7), the intro line and the accuracy note. The privacy note moved to a footer, without the "Do not upload images with private information." line.
- Paste and drag and drop anywhere on the page. Picker, paste and drop all go through `handleFile()`, so the same checks apply. Inputs are ignored while a request runs.
- "Working, 12 s." progress, with "The server may be busy." from 20 s.
- "Try another image" reset. Dark mode through CSS variables and `prefers-color-scheme`.

**Checks:** stubbed `fetch` and synthetic events: every input path accepts PNG and rejects other types and oversize files, the timer counts and clears, reset clears everything, error messages unchanged, no console errors. Light, dark and 375 px wide with no sideways scroll. `pytest`: 61 passed.

**Open points**
- Real drag from Finder and real clipboard paste (only synthetic events). Safari and Firefox.
- After a paste or drop the file picker shows "No file chosen"; the preview shows the picked image.

## T5c Result actions

**Goal:** let the user check a guess quickly on Google Fonts.
**Files:** `index.html` (369 lines).

**Changes**
- The best-guess name is a highlighted link to a Google Fonts search, and the alternatives are link chips. All open in a new tab with `rel="noopener noreferrer"`.
- Every link comes from `googleFontsSearchUrl()`: a fixed `https://fonts.google.com/?query=` plus `encodeURIComponent(name)`, so a name from the model cannot change where a link goes.
- "Unknown" has no link. A Copy button and a separate "Search on Google Fonts" link were tried and removed.

**Checks:** stubbed `fetch`: `Playfair & <b>Display</b>` shown as text and encoded in the link, `javascript:alert(1)` became a harmless search, chips replaced on each result, "Unknown" has no link. The URL format checked for real on Google Fonts (Playfair Display first). `pytest`: 61 passed.

**Open points**
- On phones the tooltip does not show, so the link colour is the only hint.
- With "Unknown" and no alternatives, "Could also be:" is shown empty.

## T6a Security hardening

**Goal:** close the gaps from the security review before the backend URL is public. Findings are in `ISSUES.md`.
**Files:** `backend/main.py`, `backend/tests/test_parser.py`, `backend/tests/conftest.py` (new), `backend/tests/test_security.py` (new).

**Changes**
- Quota cap and API restriction set on the Gemini key in Google's console.
- `RateLimiter`: 5 requests per minute per IP and 30 in total, in memory with a lock, checked after the upload checks so only requests that would call Gemini count. Blocked requests get 429.
- `/docs`, `/redoc` and `/openapi.json` off.
- `DetectResult` limits: names and size label 100 characters, reasoning 500, at most 5 alternatives, sizes 0 to 1000 px.
- CORS allows no extra request headers.
- Not done: privacy line, pinning (now T6b), CSP.

**Checks**
- `pytest`: 82 passed (21 new). Removing each protection in a throwaway copy made the tests fail every time.
- Local uvicorn with a fake key (no quota used): docs URLs 404; 7 quick uploads gave 502 five times, then 429 twice without a Gemini call; a custom header from the allowed origin was refused, and a normal POST still gets the CORS header.

**Open points**
- Which IP the app sees behind Render's proxy. If it is Render's own, every user shares 5 per minute (T6).
- Counts reset when the server restarts. The console quota cap is the daily limit.
- Calls that fail at Gemini still use a slot.

## T7 README and doc cleanup

**Goal:** a correct public README and clean docs before the repository goes public.
**Files:** `ReadMe.md`, `images/` (new), `backend/main.py`, `backend/tests/test_detect.py`, `backend/tests/test_parser.py`, `backend/tests/test_security.py`.

**Changes**
- `ReadMe.md` rewritten to match the project: features, how it works (mermaid diagram with the model fallback), the real accuracy numbers, limitations, privacy, the `/detect` API with field limits and an error table, security measures, tests, project structure, planned deployment and the licence.
- Two screenshots of the page in `images/` (start page and an Inter result), shown at the top of the README.
- `reasoning` removed from the prompt and from `DetectResult`, so `/detect` returns 7 fields, matching what the page shows. A `reasoning` key the model still sends is dropped. Tests: 2 removed, 1 added.
- `PROGRESS.md`, `ISSUES.md` and `TASKS.md` reorganized and reworded: no personal names, no rules for maintaining the files, open issues first.
- The commit log file was made local only (gitignored).

**Checks**
- `pytest`: 81 passed (82, minus 2 reasoning tests, plus 1). `/detect` with a fake model reply that includes `reasoning` returns exactly 7 keys.
- Every README fact checked against `backend/main.py` and `index.html`: limits, error messages, model names, timeouts, test counts per file.
- Render's docs: the start command `uvicorn main:app --host 0.0.0.0 --port $PORT` matches the FastAPI guide. A sleeping free service takes "about one minute" to wake up, not 30 to 50 s.
- README rendered: tables, code blocks, the mermaid diagram and both screenshots display correctly.
- No key in any tracked file or in the git history, and no metadata in the screenshots.

**Open points**
- `LICENSE` is not in the repository yet, while the README refers to it (to be added on GitHub after pushing).
- No real Gemini call with the prompt without `reasoning`. Accuracy may change slightly in either direction.
- Render's wake-up time plus a slow Gemini answer can pass the page's 90 s limit (open issue in `ISSUES.md`, check in T6).
