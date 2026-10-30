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

## T3 Tests for the parser (done)

**Files changed**
- `backend/tests/test_parser.py` (new)
- `TASKS.md`, `AGENTS.md` (branch check added as step 0)

**What was done**
- 28 tests call `parse_gemini_response()` directly. There is no HTTP and no Gemini call.
- Passing cases: plain JSON with every field checked, ```` ```json ```` fence, plain fence, text around the JSON, "Unknown" family, equal min and max size, an extra key.
- Failing cases (`ValueError`): prose, empty, whitespace, broken JSON, a JSON list, each of the 8 keys missing, a bad `alternatives` type, a bad `sizeMinPx` type, a bad `confidence` value, a bad `category` value, min larger than max.
- The error message never contains the model text.
- `/detect` returns 502 on a bad reply, with Gemini mocked, and the model text is not in the response.

**Checks run**
- `python3 -m pytest -q`: 37 passed (9 old, 28 new).

**Found, not fixed** (would change validation or the schema, so it is Leo's call)
- Pydantic's lax mode accepts a numeric string: `"sizeMinPx": "14"` becomes `14.0`. Harmless, but the reply is not strictly the shape the prompt asks for.
- An empty `family` (`""`) passes validation.

**Not verified**
- No real Gemini call yet.

### T3 follow-up: empty family (done)
- Leo's call: reject an empty or whitespace-only `family`, keep accepting numeric strings like `"14"`.
- `parse_gemini_response()` now raises `ValueError` when `family.strip()` is empty, so `/detect` returns 502 instead of a blank font name.
- New test `test_empty_family_raises` covers `""` and `"   "`.
- `python3 -m pytest -q`: 39 passed.

## T3b Upload size limit fix (done)

**Files changed**
- `backend/main.py`, `backend/tests/test_detect.py`
- `TASKS.md`, `DECISIONS.md`, `ISSUES.md`

**What was done**
- `MAX_UPLOAD_BYTES` lowered from 2 MB to 1 MiB, with one shared message `TOO_LARGE_DETAIL`.
- New `BodySizeLimitMiddleware`: wraps `receive`, counts request body bytes and raises `HTTPException(413)` before handing over the chunk that passes the limit. FastAPI turns that into a normal 413. No `Content-Length` shortcut, so middleware order with CORS does not matter.
- The upload parser never sees more than 1 MiB, so the image stays under Starlette's 1 MiB in-memory limit and never reaches disk.
- The wrong comment in `detect()` is fixed. The size check there stays as a backstop.

**Checks run**
- `python3 -m py_compile backend/main.py backend/tests/test_detect.py`: ok.
- `python3 -m pytest -q`: 44 passed (39 old, 5 new: chunked upload, just-under-limit stays in memory, middleware stops reading, middleware passes small and exactly-at-limit bodies).
- Throwaway check without the middleware: a 1.5 MiB upload triggers `rollover` once and a just-under-1 MiB upload does not, so the in-memory test can really fail.

**Not verified**
- No uvicorn run and no real Gemini call.
- TestClient joins chunked bodies into one message, so chunk-by-chunk counting is proven by the direct middleware test, not end to end.
- Behaviour behind Render's proxy is unknown.

## T4 Real image check (paused, no results yet)

**Files changed**
- `TASKS.md`, `GITREPORT.md`, `AGENTS.md` (stale doc fixes), `ISSUES.md`, `progress.md`
- `backend/main.py` untouched (timeout was tried at 45 s and reverted to 30 s)

**What was done**
- Started uvicorn locally and sent each `samples/` image once. All 5 failed:
  - Inter: 504. Playfair Display: 503. JetBrains Mono: 504. Dancing Script: 503. Bungee: 504.
- Tried `GEMINI_TIMEOUT_SECONDS` = 45 and sent Inter once more: 503 after about 3 s. Reverted to 30.
- Leo paused T4 to work on T5 and come back later.

**Checks run**
- 5 real `/detect` calls, then 1 more with the 45 s timeout. None returned a font.
- The error mapping worked: Gemini 503 became "busy" (503), a timeout became 504, no traceback.

**Not verified**
- Whether the code works on a real successful Gemini reply. No font family, size range or prompt result has been seen.
- The cause of the 504s. The 503s come from Gemini, so they are not our code. Nothing was checked beyond status codes.
- The stylized-lettering prompt decision. It needs real Dancing Script and Bungee results.

**To resume**
- Retry one image first (Inter), then the other four, once Gemini answers.
- Do not deploy (T6) before at least one real image has passed.

## T5 Write `index.html` (done)

**Files changed**
- `index.html` (new, repo root)
- `TASKS.md`, `DECISIONS.md`, `progress.md`

**What was done**
- One static page, vanilla JS. File input with preview, "Find font" button, result card, privacy note about Gemini.
- Before upload it rejects wrong types and files over 1 MiB with a clear message.
- `fetch` to `API_URL + "/detect"` with form field `file`. Shows a loading message for the cold start, a 90 s timeout via `AbortController`, and the backend's `detail` text on errors.
- Size is shown as a range. Backend text goes in with `textContent`, so no HTML from the reply is parsed.
- `API_URL` is `http://127.0.0.1:8000` for now. Change it to the Render URL in T6.

**Checks run**
- Served a copy of `index.html` from the scratchpad with `python3 -m http.server` (not the repo root, which would expose `.env`), opened it in the built-in browser, and stubbed `fetch`. Results seen:
  - wrong file type: message shown, button disabled
  - file of 1 MiB + 1 byte: "too large" message. Exactly 1 MiB: accepted
  - loading state while waiting, then result card ("Inter", "14 to 18 px (body text)", alternatives)
  - reply text containing `<b>` was shown as text, not parsed
  - stubbed 503 and 413 show the backend `detail`. A non-JSON 500 shows a status message. A network failure shows "Could not reach the server"
- `python3 -m pytest -q`: 44 passed (backend untouched).

**Not verified**
- No real request to the backend or Gemini. T4 is paused, and Gemini returned 503/504.
- The 90 s timeout message was not triggered.
- CORS from a real origin: the page was never sent to the real backend. `ALLOWED_ORIGINS` needs the GitHub Pages URL at T6.
- Looks only checked at desktop size in one browser. Not checked on a phone.
- GitHub Pages hosting and Render cold start timing.

## T4 retry: timeout and prompt (in progress, branch `t4b-prompt-timeout`)

**Files changed so far (uncommitted)**
- `backend/main.py`: `GEMINI_TIMEOUT_SECONDS` 30 to 60, and a new `PROMPT`
- `AGENTS.md`: prompt block updated to match `main.py` (checked identical with a script)
- `progress.md`, `ISSUES.md`, `DECISIONS.md`

**Real results with the old prompt (2026-10-21 and 2026-10-22, 30 s then 60 s timeout)**

| Image | True font | Answer | Family right | Category right | Confidence |
|---|---|---|---|---|---|
| Inter | Inter | Helvetica | no (close) | yes | high |
| JetBrains Mono | JetBrains Mono | Letter Gothic | no | yes | high |
| Bungee, run 1 | Bungee | Bungee | yes | yes | high |
| Bungee, run 2 (via `index.html`) | Bungee | Russo One | no | no (sans-serif) | high |
| Dancing Script | Dancing Script | Snell Roundhand | no | yes | high |
| Playfair Display | Playfair Display | no answer yet (503 and 504 only) | | | |

- 1 of 5 answers correct, category right 4 of 5, every answer "high". Every wrong answer was a classic or system font.
- Successful calls took 15 to 30 s (Bungee once 29.6 s). Several calls timed out at exactly 30 s.

**Timeout step**
- Raised `GEMINI_TIMEOUT_SECONDS` to 60. With 60: Dancing Script and Playfair gave fast 503s, then Dancing Script alone gave 200 in 15.3 s.
- So this run does not prove 60 s helps (15 s would also pass at 30 s). Kept 60 as a margin because real calls already reach 30 s, and it still fits under the frontend's 90 s.

**Prompt step**
- Removed "prefer well-known names", added a letterform checklist, said Google Fonts and modern UI and coding fonts are in scope, limited "high" confidence to clear matches, and asked the reasoning to separate the pick from the alternatives. Same 8 keys and allowed values, so the parser is untouched. Sample font names were not put in the prompt on purpose.
- Claude's test run: Inter 503 (9.1 s), Playfair 503 (2.4 s), then stopped after two 503s in a row. Stopping on one 503 per image made Gemini look worse than it is.
- Leo's runs through `index.html` (2026-10-22, new prompt). A 503 was retried by hand:

| Image | Answer | Family right | Category right | Confidence | Tries |
|---|---|---|---|---|---|
| Playfair Display | Playfair Display | yes | yes | high | 2 (503, then 200) |
| JetBrains Mono | OCR-B | no | yes | high | 3 (503, 503, then 200) |
| not recorded | wrong family | no | yes | not recorded | 2 (503, then 200) |

- Confidence was still "high" on a wrong answer, so the new confidence rule did not work.

**Category accuracy (all successful answers, both prompts)**
- 7 of 8 correct. The one miss was Bungee as "sans-serif" (display and sans-serif overlap).
- Font family: 2 of 8 correct.
- Small sample, and each sample is a clear textbook example of its category. Real screenshots will likely be harder (not measured).
- Idea for later (Leo, not done yet): show the category first and the family as a best guess.

**503 pattern**
- Gemini often returns 503 on the first 1 or 2 tries and answers on the next. Testing rule at the time: retry an image at least 3 times on 503 before calling it failed. Dropped after T4b, because the new models gave no 503.

**Checks run**
- `python3 -m py_compile backend/main.py`: ok. `python3 -m pytest -q`: 44 passed.

**Not verified**
- Whether the new prompt is better overall. Only 3 answers so far with it, from different images than the old run.
- Size accuracy (true sizes of the samples are unknown).

**To resume**
- One final run of all 5 samples with the new prompt, up to 3 tries per image on 503. Then fill in the table and close T4.

## T4b Gemini model fallback (done)

**Files changed**
- `backend/main.py`, `backend/tests/test_gemini_fallback.py` (new)
- `TASKS.md`, `progress.md`, `ISSUES.md`, `GITREPORT.md`, plus `DECISIONS.md` and `AGENTS.md` (both gitignored)

**What was done**
- Replaced `MODEL`, `GEMINI_URL` and `GEMINI_TIMEOUT_SECONDS` with one list `MODELS` of (name, timeout): `gemini-3-flash-preview` 40 s, `gemini-3.5-flash-lite` 20 s, `gemini-3.1-flash-lite` 20 s. Total 80 s, under the page's 90 s.
- `call_gemini()` loops over `MODELS`. A 503, 429, timeout or other 5xx moves on to the next model. A 400, 401, 403, 404 or network error stops at once with 502. If all three fail, the user gets the last error, so the messages are the same as before.
- One log line per attempt with uvicorn's logger (model name and status only, never the image or the key), e.g. `gemini-3-flash-preview: timed out after 40 s, trying next model`.
- Prompt, parser, `detect()` and the response schema are unchanged.

**Checks run**
- `python3 -m py_compile backend/main.py backend/tests/test_gemini_fallback.py`: ok.
- `python3 -m pytest -q`: 61 passed (44 old, 17 new). New tests use a fake `requests.post` and check the order of models and timeouts, each fallback reason, the last error when all fail, no fallback on 400/401/403/404 and network errors, no call without a key, and that the timeouts add up to under 90 s.
- Real run, 2026-10-23, new prompt, up to 3 tries per image on 503 (none were needed):

| Image | Answer | Family right | Category right | Confidence | Model that answered | Time |
|---|---|---|---|---|---|---|
| Inter | Inter | yes | yes | high | `gemini-3.5-flash-lite` (first model timed out at 40 s) | 41.5 s |
| Playfair Display | Playfair Display | yes | yes | high | `gemini-3-flash-preview` | 6.6 s |
| JetBrains Mono | DM Mono | no | yes | high | `gemini-3-flash-preview` | 14.8 s |
| Dancing Script | Great Vibes | no | yes | high | `gemini-3-flash-preview` | 5.2 s |
| Bungee | Russo One (Bungee in alternatives) | no | no (sans-serif) | high | `gemini-3-flash-preview` | 13.6 s |

- Family 2 of 5, category 4 of 5. No 503 at all, against most calls failing with `gemini-3.8-flash` in T4. The fallback was used for real once (Inter).
- Calls were faster: 5 to 15 s on the first model, against 15 to 30 s before.

**Not verified**
- One run only. Fewer 503s may be the new model or just a quiet day.
- That the tests can fail: no deliberate break of the code was tried.
- Size accuracy (true sizes unknown).
- Behaviour on Render.

**Notes**
- Inter needed 41.5 s, close to the edge: a page waiting 90 s still has room, but a slow first model costs 40 s before the backup starts.
- Confidence is still always "high". Accuracy of the family name is still poor, so T5b (lead with category) still makes sense.

## T5b Layout revamp (done)

**Files changed**
- `index.html`
- `TASKS.md`, `progress.md`, `ISSUES.md`, `GITREPORT.md`, plus `DECISIONS.md` (gitignored)

**What was done**
- Result card leads with the category ("Serif", from a small `CATEGORY_LABELS` map, unknown values shown as they are), then "Best guess: <family>" and "Could also be: <alternatives>". Confidence and size stay in the list.
- Follow-up (Leo's call, same task): removed the "Why" field (the model's reasoning), the intro line and the accuracy note under the card. The privacy note moved to a footer at the bottom of the page. The backend still sends `reasoning`, the page just does not show it.
- Paste (Ctrl or Cmd + V anywhere) and drag and drop (anywhere on the page, so a missed drop does not open the image in the browser). Picker, paste and drop all call `handleFile()`, which runs the existing type and 1 MiB checks. The click handler sends `selectedFile` instead of reading the picker.
- Progress text "Working, 12 s." updated every second, with a "may be busy" hint from 20 s (Leo shortened it to "The server may be busy." before committing). Stopped in the `finally` block, so it ends on success, error and timeout.
- While a request runs, the picker, paste and drop are ignored (`busy` flag), so the shown result always matches the preview.
- "Try another image" button after a result or an error. It clears the file, picker, preview, status and result. Old preview URLs are freed with `URL.revokeObjectURL`.
- Dark mode: colours moved into CSS variables, overridden in one `prefers-color-scheme: dark` block.
- 175 to 328 lines. More than the 260 I estimated: the CSS variables, the dark block and the drag and drop handlers took more room.

**Checks run**
- Served a copy from the scratchpad (not the repo root) and tested in the built-in browser with a stubbed `fetch` and synthetic events:
  - picker, drop and paste: `.txt` and GIF rejected, 1 MiB + 1 byte rejected, PNG accepted; pasting plain text changes nothing
  - drop highlights the box on dragover, clears it on drop, and the drop is prevented from opening the file
  - progress: "Working, 0 s.", "Working, 12 s.", "Working, 23 s. The server may be busy or waking up." (clock faked), then cleared after the reply and still clear 1 s later
  - a paste during a request is ignored
  - card order: label, category, best guess, alternatives, list; `<b>` in the reply shown as text; unknown category "blackletter" shown as is
  - after the follow-up: page order is title, drop zone, buttons, preview, status, result, footer with the privacy note; the reasoning text never appears on the page; no console errors
  - reset clears everything; 503 detail, non-JSON 500, network error and timeout messages unchanged, and the reset button appears after each
  - screenshots in light and dark mode, and at 375 px wide with no sideways scroll
- `python3 -m pytest -q`: 61 passed (backend untouched).

**Not verified**
- Real drag from Finder and real clipboard paste of a screenshot (only synthetic events). Safari and Firefox. No real Gemini request through the new page.

**Notes**
- Leo's own edits before the commit: drop-zone text shortened to "paste it" (no shortcut shown), preview moved below the status line, and "Do not upload images with private information." removed from the privacy note. All intentional.
- After a paste or drop the file picker shows "No file chosen", because it was cleared on purpose. The preview shows which image is picked.

## T5c Result actions (done)

**Files changed**
- `index.html`
- `TASKS.md`, `progress.md`, `GITREPORT.md`, plus `DECISIONS.md` (gitignored)

**What was done**
- A "Copy" button next to the font name was built and tested, then removed (Leo's call). The name is a link now, so the button was extra clutter.
- The best-guess font name itself is the Google Fonts search link (highlighted, tooltip "Search Google Fonts for this name"), opening in a new tab with `rel="noopener noreferrer"`. A first version had a separate "Search on Google Fonts" text link; Leo asked to merge it into the name.
- Alternatives are now chips (links) that search Google Fonts the same way. Built with `createElement` and `textContent`, and emptied with `replaceChildren()` before each new result.
- Every link comes from one function, `googleFontsSearchUrl()`: a fixed `https://fonts.google.com/?query=` plus `encodeURIComponent(name)`, so a name from the model cannot change where a link goes.
- When the family is "Unknown" (the prompt's answer for no readable text), the name loses its `href`, so it shows as plain text.
- The T5b full stop in "The server may be busy." was fixed by Leo on this branch.
- After removing Copy: no `copyButton`, `shownFamily` or clipboard code left (checked with grep); the line reads "Best guess: Russo One" with the link; "Unknown" has no link; reset works; no console errors. 381 to 369 lines.
- 322 to 381 lines.

**Checks run**
- Served a copy from the scratchpad and tested in the built-in browser with a stubbed `fetch`:
  - family `Playfair & <b>Display</b>`: shown as text, link `?query=Playfair%20%26%20%3Cb%3EDisplay%3C%2Fb%3E`
  - an alternative named `javascript:alert(1)` became `https://fonts.google.com/?query=javascript%3Aalert(1)`, a harmless search
  - every link starts with `https://fonts.google.com/?query=`, has `target="_blank"` and `rel="noopener noreferrer"`
  - 3 chips for 3 alternatives; a second result replaced them (2 chips), not added to them
  - (before the Copy button was removed) Copy with a stubbed clipboard: "Copied", clipboard got "Inter", back to "Copy" after 2 s. Rejected write and missing clipboard API: "Copy failed"
  - "Unknown" removes the link; the next real result brings it back
  - after merging the link into the name: name "Russo One" links to `?query=Russo%20One`, no "Search on Google Fonts" text left; "Unknown" has no `href` and plain text colour
  - reset still clears the card; no console errors
  - screenshots in light mode, dark mode and at 375 px (chips wrap, no sideways scroll)
- Opened `https://fonts.google.com/?query=Playfair%20Display` in the built-in browser: Google Fonts shows "2 of 1,951 families" with Playfair Display first, so the URL format works.
- `python3 -m pytest -q`: 61 passed (backend untouched).

**Not verified**
- Safari and Firefox, a real Gemini request through the page.
- On phones the tooltip does not show, so nothing says the name is a search; the link colour is the only hint.

**Notes**
- With "Unknown" and no alternatives, "Could also be:" is shown with nothing under it.

## T6a Security hardening (done, parts 2 and 4)

**Files changed**
- `backend/main.py`, `backend/tests/test_parser.py`, `backend/tests/conftest.py` (new), `backend/tests/test_security.py` (new)
- `TASKS.md`, `progress.md`, `ISSUES.md`, `GITREPORT.md`, plus `DECISIONS.md` (gitignored)

**What was done**
- Part 1 (Leo): quota cap and API restriction on the Gemini key in Google's console.
- Part 2: `RateLimiter` class. A dict of recent request times per client IP plus one list for everyone, a lock because `detect()` runs in several threads, and idle IPs are removed. `detect()` checks it after the upload checks and before Gemini, so a rejected upload costs no slot and a blocked request costs no quota. Limits: 5 per minute per IP, 30 in total. Answer: 429 "Too many requests. Try again in a minute.", which the page already shows.
- Part 4: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`. `DetectResult` limits through `Field`: names and size label 100 characters, reasoning 500, alternatives at most 5, sizes 0 to 1000 px (0 allowed, not 1 as first planned, because an "Unknown" answer may have no size). CORS `allow_headers=[]`.
- `conftest.py` gives every test a fresh limiter, so tests that call `/detect` never block each other.
- Not done: part 3 (privacy line, Leo said no), part 5 (pinning), part 6 (CSP).

**Checks run**
- `python3 -m py_compile` on the changed files: ok. `python3 -m pytest -q`: 82 passed (61 old, 21 new).
- Each protection was removed on purpose in a throwaway copy, and the tests failed every time: no per-IP limit (6 failed), no total cap (1), docs back on (3), no length cap (3), no size range (2), limiter moved before the upload checks (2).
- Local uvicorn with a fake key (so Gemini refused it with 400 and no quota was used) and `ALLOWED_ORIGINS=http://127.0.0.1:5500`:
  - `/docs`, `/redoc`, `/openapi.json`: 404
  - `/detect` 7 times from one IP: 5 times 502 (fake key, no fallback on 400), then 429 twice without a Gemini call (log shows no model line)
  - preflight from the allowed origin asking for a custom header `X-Custom`: 400 (refused)
  - a plain POST from the allowed origin still gets `access-control-allow-origin`, so the page can read the 429 message

**Not verified**
- How Render's proxy passes the client IP. If the app sees Render's IP, every user shares the 5 per minute. Check in T6.
- The `test_cors_preflight_from_unknown_origin_is_refused` test passes with or without the `allow_headers` change (no origin is allowed in tests). The `allow_headers` change was checked by hand with curl above.

**Notes**
- Calls that fail at Gemini still use a slot, since they did call Gemini.
