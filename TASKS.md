# TASKS.md

Only one task is "In progress" at a time. 

## In progress

T5
## Next

### T4 Real image check
- Run `/detect` against the 5 images in `samples/` (Inter, Playfair Display, JetBrains Mono for plain text; Dancing Script and Bungee for stylized lettering). Record the results.
- Decide whether to add the stylized-lettering line to the prompt
- Paused 2026-10-20: all real Gemini calls returned 503 or 504 (see `ISSUES.md`, `progress.md`). Retry one image first later.

### T6 Deploy (Leo)
- Backend to Render with `GEMINI_API_KEY` set in the dashboard, frontend to GitHub Pages, point `index.html` at the Render URL
- Do not deploy until T4 has at least one real successful image result

### T7 Update README
- Python backend setup, `/detect` request and response shape, limitations, privacy note

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
