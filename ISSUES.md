# ISSUES.md

Every bug, error or issue found in the project, with where it is, what it does and its status. Open issues come first, then mitigated, then fixed.

## Status overview

| Issue | Status | Handled in |
|---|---|---|
| Gemini often names the wrong font, always with "high" confidence | Open (mitigated in the UI) | T4, T4b, T5b |
| Privacy footer does not say what Google may do with images | Open | Not changed in T6a |
| Dependencies are not pinned | Open | Planned as T6b |
| Deploy settings must be right | Open | T6 |
| `reference/test.py` puts the key in the URL | Open | Not changed (reference file) |
| First request after Render sleeps can pass the page's 90 s limit | Open | Found in T7, check in T6 |
| Real Gemini calls fail with 503 or 504 | Mitigated | T4, T4b |
| Anyone can use up the Gemini quota | Mitigated | T6a |
| Slow requests can block the server | Partly mitigated | T6a |
| Text inside an image can steer the model's answer | Mitigated | T6a |
| Uploads are fully received before the size check, and 1 to 2 MB uploads touch disk | Fixed | T3b |
| API docs pages were public | Fixed | T6a |

---

## Open

### Gemini often names the wrong font, always with "high" confidence

**Where**
- The answer from Gemini, shown by `/detect` and `index.html`. Prompt in `backend/main.py` `PROMPT`.

**Effect**
- With the old prompt, 1 of 5 real answers named the right family (see `PROGRESS.md`, T4). Category was right 4 of 5.
- Every answer said "high" confidence, so users cannot tell a good answer from a bad one.
- The same Bungee image gave two different answers (Bungee, then Russo One).

**Cause**
- Not proven. Suspect: the prompt line "prefer well-known names", since every wrong answer was a classic or system font. Also likely: a general model is not a font-matching tool, and answers vary between runs.

**Status**
- New prompt (T4, branch `t4b-prompt-timeout`, commit `4b9b9f0`). First results: Playfair Display right, JetBrains Mono wrong (OCR-B), one more wrong family. Confidence still "high" on wrong answers.
- Category is right 7 of 8 times across both prompts, so the category is more trustworthy than the family name.
- New models (T4b, one run): family right 2 of 5 (Inter, Playfair Display), category right 4 of 5 (Bungee called sans-serif). Confidence still "high" on every answer, including the 3 wrong ones.
- Mitigated in the UI (T5b): `index.html` leads with the category and shows the family as "Best guess" with "Could also be" alternatives.
- Still open: the model's accuracy itself is unchanged.

### Privacy footer does not say what Google may do with images

**Where**
- `index.html` footer.

**Effect**
- The footer says this server does not save images, which is true. The free Gemini API terms may allow Google to keep and review content (not checked). Users get no warning about private screenshots.

**Status**
- Open. Not changed in T6a (part 3 of the security plan was not done).

### Dependencies are not pinned

**Where**
- `backend/requirements.txt` has no versions, and installs `pytest` and `httpx` in production.

**Effect**
- Every deploy installs the newest versions, so a broken or bad release could go live unnoticed.

**Status**
- Open. Planned as T6b: pin the versions and move the dev tools into `requirements-dev.txt`.

### Deploy settings must be right

**Where**
- `index.html` `API_URL`, the `ALLOWED_ORIGINS` env var on Render, and GitHub Pages.

**Effect**
- `API_URL` in `index.html` must be the https Render URL. `ALLOWED_ORIGINS` on Render must be exactly the GitHub Pages origin, never `*`.
- GitHub Pages serves every tracked file in the repo root publicly (none holds a secret).

**Status**
- Open. Part of T6.

### `reference/test.py` puts the key in the URL

**Where**
- `reference/test.py:7-8`, `?key=` in the URL, with only the placeholder `"API Key"`.

**Effect**
- None today. A real key pasted there would be committed and would show up in logs.

**Status**
- Open. The file is kept unmodified as the original reference script (rule in `AGENTS.md`).

### First request after Render sleeps can pass the page's 90 s limit

Found while checking Render's docs for the README (T7).

**Where**
- `index.html` `TIMEOUT_MS = 90000`, with the comment "Render's free tier can take 30 to 50 s to wake up". The same 30 to 50 s figure is in two `DECISIONS.md` lines.
- `backend/main.py` `MODELS`: up to 80 s of Gemini timeouts in total.

**Effect**
- Render's free-tier docs (render.com/docs/free, read 2026-10-30) say a sleeping service takes "about one minute" to spin back up, not 30 to 50 s.
- About 60 s of wake-up plus a slow Gemini answer can go past 90 s, so the page would show "The server took too long to answer" even though the backend is still working.
- The same docs say Render shows a loading page to browsers while a service spins up. What a `fetch` from the page receives during that time is unknown.

**Status**
- Open. Check real wake-up times and the `fetch` behaviour in T6, then decide whether to raise `TIMEOUT_MS` or change the message.

---

## Mitigated

### Real Gemini calls fail with 503 or 504

**Where**
- `backend/main.py` `call_gemini()`, run locally with uvicorn on 2026-10-20, one request per file in `samples/`.

**Effect**
- Inter 504, Playfair Display 503, JetBrains Mono 504, Dancing Script 503, Bungee 504. A later Inter retry with a 45 s timeout gave 503 after about 3 s.
- No font result was returned on that day, so T4 had no data at first.
- Error mapping worked: 503 became "busy", the timeout became 504, no traceback.

**Cause**
- First reading (2026-10-20): the 503s come from Gemini, so likely high demand. The 504s were unexplained (Gemini hanging or the network). The 30 s timeout was thought not to be the cause. Nothing was checked beyond status codes.
- Corrected (2026-10-21 and 2026-10-22): Gemini answered some calls in 15 to 30 s, and several others hit the 30 s limit exactly (504 at 30.1 s). So the 30 s timeout did cut off slow calls. The first reading was based only on one fast 503.
- 503s still came often and in bursts.

**Status**
- Timeout raised to 60 s in commit `4b9b9f0`.
- T4b (2026-10-23): switched to `gemini-3-flash-preview` with two Flash-Lite backups, timeouts 40/20/20 s. First real run: 5 of 5 images answered on the first try, no 503. Inter's first model timed out at 40 s and the first backup answered.
- One run only, so not called fixed yet.

### Anyone can use up the Gemini quota

Found in the security review of 2026-10-27.

**Where**
- `backend/main.py` `/detect` had no limit per user, and the model fallback can make up to 3 Gemini calls per request.

**Effect**
- CORS only stops other websites. A script calling the Render URL directly could spend the whole free quota.

**Status**
- A quota cap and an API restriction were set on the key in Google's console (T6a part 1).
- `RateLimiter` allows 5 requests per minute per IP and 30 in total (T6a part 2).
- Still open: counts reset when Render restarts the server, and behind Render's proxy the app may see Render's IP instead of the user's, which would put everyone in one bucket. Check in T6.

### Slow requests can block the server

Found in the security review of 2026-10-27.

**Where**
- `detect()` is a normal function, so it runs in a pool of about 40 threads, and each request can wait up to 80 s for Gemini.

**Effect**
- About 40 slow requests at once would make the server stop answering.

**Status**
- Partly mitigated in T6a: the 30 per minute total cap makes this much harder. Not fully solved.

### Text inside an image can steer the model's answer

Found in the security review of 2026-10-27.

**Where**
- The model reads text in the image, and its answer goes to the page.

**Effect**
- Odd or very long text in the result card. No script can run: the page uses `textContent` and builds links from a fixed prefix plus `encodeURIComponent`.

**Status**
- Mitigated in T6a: `DetectResult` now limits names and size label to 100 characters, reasoning to 500, alternatives to 5, sizes to 0 to 1000 px. Anything outside becomes 502.
- T7: `reasoning` is no longer asked for or returned, so the free text the model writes is gone from the API. A `reasoning` key sent anyway is dropped.

---

## Fixed

### Uploads are fully received before the size check, and 1 to 2 MB uploads touch disk

**Where** (line numbers from before the fix)
- `backend/main.py:147` `detect(file: UploadFile = File(...))`: FastAPI receives and stores the whole upload before `detect()` runs.
- `backend/main.py:149` `file.file.read(MAX_UPLOAD_BYTES + 1)` only limits what the code reads, not what the server received.
- Cause in Starlette (0.49.3): `starlette/formparsers.py:126` keeps an upload in memory up to 1 MiB, then rolls it to a temp file on disk.

**Effect**
- A 1 to 2 MB screenshot is briefly written to the server's temp folder. This breaks the "never save images" rule.
- No real size cap: a 500 MB upload is received and spooled in full, then rejected at `main.py:152`.
- The comment at `main.py:148` ("detected without loading all of it") is wrong.

**Chosen fix**
- Lower `MAX_UPLOAD_BYTES` to 1 MiB (`1024 * 1024`).
- Add a small ASGI middleware that counts request body bytes as they arrive and raises `HTTPException(413)` once the total passes 1 MiB. FastAPI re-raises an `HTTPException` raised while reading the body (`fastapi/routing.py:401-403`), so it becomes a normal 413 response.
- Why it works: the parser never sees more than 1 MiB, and the image is the body minus the multipart wrapper, so it stays under Starlette's 1 MiB spool limit and never reaches disk. It also works for uploads without `Content-Length` (chunked).
- Rejected: raw request body (bigger change to request format, tests and docs) and a `Content-Length`-only check (chunked uploads skip it, and 1 to 2 MB files still spool).

**Rules for the fix**
- Raise `HTTPException`, not a plain exception. Anything else becomes a 400 (`fastapi/routing.py:404-407`).
- No separate `Content-Length` shortcut that sends its own response. Outside CORS, the browser would see a CORS error instead of the 413.
- Fix the comment at `main.py:148`. Keep the check at `main.py:152` as a backstop.
- Update the 2 MB line in `DECISIONS.md` to 1 MB. Reason: screenshots are 100 to 300 KB, and staying under the 1 MiB spool keeps images off disk.

**Tests added with the fix**
- Upload over 1 MiB returns 413 and Gemini is not called.
- Upload over 1 MiB without `Content-Length` (chunked) returns 413.
- A just-under-limit image never rolls to disk (fails if `SpooledTemporaryFile.rollover` is called). Guards against a Starlette update lowering the spool limit, since `requirements.txt` is unpinned.
- Middleware unit test: it stops reading as soon as the limit is passed.

**Accepted limits**
- An oversized upload still uses bandwidth: uvicorn reads and discards the rest (`uvicorn/protocols/http/h11_impl.py:260-262`). Nothing is stored.
- A browser still uploading may show a network error instead of the 413. The page (T5) checks `file.size` before sending.

**How it was found**
- By reading library source only, before the fix. Render's proxy behaviour with large bodies is unknown.

**Fixed in T3b (branch `fix-upload-limit`)**
- `MAX_UPLOAD_BYTES` is now 1 MiB, and `BodySizeLimitMiddleware` in `backend/main.py` counts body bytes and raises 413 once the total passes it.
- The check in `detect()` is now a backstop and its comment is corrected.
- Tests in `backend/tests/test_detect.py`: chunked upload without `Content-Length` returns 413, a just-under-limit image never rolls to disk, and the middleware stops reading after the limit and passes small bodies through.
- `python3 -m pytest -q`: 44 passed.

### API docs pages were public

Found in the security review of 2026-10-27.

**Where**
- FastAPI served `/docs`, `/redoc` and `/openapi.json` by default.

**Effect**
- A ready-made upload form and a list of the API for anyone.

**Status**
- Fixed in T6a: all three return 404.
