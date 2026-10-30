# TASKS.md

Only one task is "In progress" at a time. 

## Optional

### T5d Sample images (optional experiment)
- Sample buttons so a visitor without a screenshot can try it. Own images only. Each click uses Gemini quota

- Shrink images over 1 MiB in the browser. Keep only if a test on the 5 samples shows no loss in accuracy, since shrinking also shrinks the letters

### T6b Pin dependencies (planned, from T6a part 5)
- Exact versions in `backend/requirements.txt`, `pytest` and `httpx` moved to a new `backend/requirements-dev.txt`.

## Next

### T6 Deploy
- Backend to Render with `GEMINI_API_KEY` set in the dashboard, frontend to GitHub Pages, point `index.html` at the Render URL
- `API_URL` must be the https Render URL, `ALLOWED_ORIGINS` exactly the GitHub Pages origin
- Check which IP the rate limiter sees behind Render's proxy (uvicorn `--proxy-headers`). If it is Render's own IP, every user shares 5 per minute

### T7b README after deploy
- Add `LICENSE` (MIT) on GitHub after pushing `main`; the README already refers to it
- Live demo link, the real wake-up time on Render and the result of the rate-limit IP check

## Done

### T1
- Gemini API key created on the free tier
- `test.py` works end to end with `gemini-3.8-flash`
- API key moved into `.env`, and `.env` is gitignored
- Prompt chosen
- T1 Scaffold the FastAPI backend (see `PROGRESS.md`): 9 upload validation tests pass

### T2
- T2 Parse and validate the Gemini response (see `PROGRESS.md`): checked by hand, tests are T3

### T3
- T3 Tests for the parser (see `PROGRESS.md`): 28 new tests in `backend/tests/test_parser.py`, 37 pass in total
- T3b Upload size limit fix (see `PROGRESS.md`, `ISSUES.md`): 1 MiB limit plus byte-counting middleware, 44 tests pass

### T4
- T4 Real image check (see `PROGRESS.md`, `ISSUES.md`): pipeline works end to end on real images. Category right 7 of 8, family 2 of 8, confidence always "high", frequent Gemini 503s. Timeout raised to 60 s and prompt rewritten (commit `4b9b9f0`). No separate stylized-lettering line needed. The full new-prompt comparison moves to T4b, since the model changes
- T4b Gemini model fallback (see `PROGRESS.md`, `ISSUES.md`): `gemini-3-flash-preview` 40 s, then `gemini-3.5-flash-lite` 20 s, then `gemini-3.1-flash-lite` 20 s. 61 tests pass. Real run: 5 of 5 answered, no 503, family 2 of 5, category 4 of 5

### T5
- T5 Write `index.html` (see `PROGRESS.md`): file check, loading state, result card, error messages. Checked with a stubbed `fetch`, not against real Gemini (done while T4 was paused)
- T5b Layout revamp (see `PROGRESS.md`): category first with the family as a best guess, paste and drag and drop through one `handleFile()`, "Working, N s" progress, "Try another image" reset, dark mode. Checked with a stubbed `fetch` and synthetic events, not with a real paste, drag or Gemini call
- T5c Result actions (see `PROGRESS.md`): the best-guess name links to a Google Fonts search, alternatives as link chips, all links built by one encoding function. No link for "Unknown". Copy button built, then removed. Checked with a stubbed `fetch`; the Google Fonts URL format checked for real

### T6
- T6a Security hardening (see `PROGRESS.md`, `ISSUES.md`): quota cap and key restriction in Google's console, rate limit 5 per minute per IP and 30 in total, API docs off, limits on the model's answer, CORS without extra headers. 82 tests pass

### T7
- T7 README and doc cleanup (see `PROGRESS.md`): README rewritten with screenshots, accuracy numbers, API and security sections; `reasoning` dropped from the API (81 tests pass); `PROGRESS.md`, `ISSUES.md` and `TASKS.md` reorganized. `LICENSE` still to add (T7b)
