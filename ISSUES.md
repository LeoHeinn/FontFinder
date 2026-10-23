# ISSUES.md

Every bug, error or issue found in the project. One entry per issue, status in the title (open, fix chosen, fixed). New entries go at the bottom.

### Uploads are fully received before the size check, and 1 to 2 MB uploads touch disk (fixed in T3b)

**Where**
- `backend/main.py:147` `detect(file: UploadFile = File(...))`: FastAPI receives and stores the whole upload before `detect()` runs.
- `backend/main.py:149` `file.file.read(MAX_UPLOAD_BYTES + 1)` only limits what our code reads, not what the server received.
- Cause in Starlette (0.49.3): `starlette/formparsers.py:126` keeps an upload in memory up to 1 MiB, then rolls it to a temp file on disk.

**Effect**
- A 1 to 2 MB screenshot is briefly written to the server's temp folder. This breaks the "never save images" rule.
- No real size cap: a 500 MB upload is received and spooled in full, then rejected at `main.py:152`.
- The comment at `main.py:148` ("detected without loading all of it") is wrong.

**Chosen fix (Leo's approach)**
- Lower `MAX_UPLOAD_BYTES` to 1 MiB (`1024 * 1024`).
- Add a small ASGI middleware that counts request body bytes as they arrive and raises `HTTPException(413)` once the total passes 1 MiB. FastAPI re-raises an `HTTPException` raised while reading the body (`fastapi/routing.py:401-403`), so it becomes a normal 413 response.
- Why it works: the parser never sees more than 1 MiB, and the image is the body minus the multipart wrapper, so it stays under Starlette's 1 MiB spool limit and never reaches disk. It also works for uploads without `Content-Length` (chunked).
- Rejected: raw request body (bigger change to request format, tests and docs) and a `Content-Length`-only check (chunked uploads skip it, and 1 to 2 MB files still spool).

**Rules for the fix**
- Raise `HTTPException`, not a plain exception. Anything else becomes a 400 (`fastapi/routing.py:404-407`).
- No separate `Content-Length` shortcut that sends its own response. Outside CORS, the browser would see a CORS error instead of the 413.
- Fix the comment at `main.py:148`. Keep the check at `main.py:152` as a backstop.
- Update the 2 MB line in `DECISIONS.md` to 1 MB. Reason: screenshots are 100 to 300 KB, and staying under the 1 MiB spool keeps images off disk.

**Tests to add with the fix**
- Upload over 1 MiB returns 413 and Gemini is not called.
- Upload over 1 MiB without `Content-Length` (chunked) returns 413.
- A just-under-limit image never rolls to disk (fail if `SpooledTemporaryFile.rollover` is called). Guards against a Starlette update lowering the spool limit, since `requirements.txt` is unpinned.
- Middleware unit test: it stops reading as soon as the limit is passed.

**Accepted limits**
- An oversized upload still uses bandwidth: uvicorn reads and discards the rest (`uvicorn/protocols/http/h11_impl.py:260-262`). Nothing is stored.
- A browser still uploading may show a network error instead of the 413. T5 should check `file.size` before sending.

**Not verified**
- Found by reading library source only. Nothing was run. Render's proxy behaviour with large bodies is unknown.

**Fixed (T3b, branch `fix-upload-limit`)**
- `MAX_UPLOAD_BYTES` is now 1 MiB, and `BodySizeLimitMiddleware` in `backend/main.py` counts body bytes and raises 413 once the total passes it.
- Line numbers above are from before the fix. The check in `detect()` is now a backstop and its comment is corrected.
- Tests in `backend/tests/test_detect.py`: chunked upload without `Content-Length` returns 413, a just-under-limit image never rolls to disk, and the middleware stops reading after the limit and passes small bodies through.
- `python3 -m pytest -q`: 44 passed.

### T4: real Gemini calls fail with 503 or 504 (mitigated in T4b)

**Where**
- `backend/main.py` `call_gemini()`, run locally with uvicorn on 2026-10-20, one request per file in `samples/`.

**Effect**
- Inter 504, Playfair Display 503, JetBrains Mono 504, Dancing Script 503, Bungee 504. A later Inter retry with a 45 s timeout gave 503 after about 3 s.
- No font result was returned, so T4 has no data yet.
- Error mapping worked: 503 became "busy", the timeout became 504, no traceback.

**Cause**
- Not known. The 503s come from Gemini, so likely high demand. The 504s are unexplained (Gemini hanging or the network). The 30 s timeout is not the cause. Nothing was checked beyond status codes.

**Update 2026-10-21 and 2026-10-22**
- Gemini answered some calls in 15 to 30 s, and several others hit the 30 s limit exactly (504 at 30.1 s). So the 30 s timeout did cut off slow calls. The statement above that it is not the cause was based only on one fast 503.
- 503s still come often and in bursts.

**Status**
- Timeout raised to 60 s in commit `4b9b9f0`.
- T4b (2026-10-23): switched to `gemini-3-flash-preview` with two Flash-Lite backups, timeouts 40/20/20 s. First real run: 5 of 5 images answered on the first try, no 503. Inter's first model timed out at 40 s and the first backup answered. One run only, so not called fixed yet.

### Gemini often names the wrong font, always with "high" confidence (open)

**Where**
- The answer from Gemini, shown by `/detect` and `index.html`. Prompt in `backend/main.py` `PROMPT`.

**Effect**
- With the old prompt, 1 of 5 real answers named the right family (see `progress.md`, T4 retry). Category was right 4 of 5.
- Every answer said "high" confidence, so users cannot tell a good answer from a bad one.
- The same Bungee image gave two different answers (Bungee, then Russo One).

**Cause**
- Not proven. Suspect: the prompt line "prefer well-known names", since every wrong answer was a classic or system font. Also likely: a general model is not a font-matching tool, and answers vary between runs.

**Status**
- Open. New prompt on `t4b-prompt-timeout`. First results: Playfair Display right, JetBrains Mono wrong (OCR-B), one more wrong family. Confidence still "high" on wrong answers.
- Category is right 7 of 8 times across both prompts, so the category is more trustworthy than the family name.
- T4b new models (one run): family right 2 of 5 (Inter, Playfair Display), category right 4 of 5 (Bungee called sans-serif). Confidence still "high" on every answer, including the 3 wrong ones. Still open.
