# TASKS.md

Only one task is "In progress" at a time. 

## In progress

None.

## Next

### T5b Lead with category in `index.html`
- Show the category first and the font family as a best guess with the alternatives, because category is right far more often (T4: 7 of 8) than family (2 of 8)
- Not started. Leo said: not yet

### T6 Deploy (Leo)
- Backend to Render with `GEMINI_API_KEY` set in the dashboard, frontend to GitHub Pages, point `index.html` at the Render URL
- Do not deploy until T4 has at least one real successful image result

### T7 Update README
- Python backend setup, `/detect` request and response shape, limitations, privacy note
- Limitations section must cover the Gemini API: frequent 503 "busy" (try again), free-tier quota, 15 to 30 s per call, font family often wrong while category is usually right, confidence not reliable, size is a rough range

## Done
- Gemini API key created on the free tier
- `test.py` works end to end with `gemini-3.8-flash`
- API key moved into `.env`, and `.env` is gitignored
- Prompt chosen
- T1 Scaffold the FastAPI backend (see `progress.md`): 9 upload validation tests pass
- T2 Parse and validate the Gemini response (see `progress.md`): checked by hand, tests are T3
- T3 Tests for the parser (see `progress.md`): 28 new tests in `backend/tests/test_parser.py`, 37 pass in total
- T3b Upload size limit fix (see `progress.md`, `ISSUES.md`): 1 MiB limit plus byte-counting middleware, 44 tests pass
- T5 Write `index.html` (see `progress.md`): file check, loading state, result card, error messages. Checked with a stubbed `fetch`, not against real Gemini
- T4 Real image check (see `progress.md`, `ISSUES.md`): pipeline works end to end on real images. Category right 7 of 8, family 2 of 8, confidence always "high", frequent Gemini 503s. Timeout raised to 60 s and prompt rewritten (commit `4b9b9f0`). No separate stylized-lettering line needed. The full new-prompt comparison moves to T4b, since the model changes
- T4b Gemini model fallback (see `progress.md`, `ISSUES.md`): `gemini-3-flash-preview` 40 s, then `gemini-3.5-flash-lite` 20 s, then `gemini-3.1-flash-lite` 20 s. 61 tests pass. Real run: 5 of 5 answered, no 503, family 2 of 5, category 4 of 5
