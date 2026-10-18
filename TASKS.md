# TASKS.md

Only one task is "In progress" at a time. 

## In progress

None. Leo moves T2 here when he starts it.

## Next

### T2 Parse and validate the Gemini response (Leo writes)
- Turn raw model text into the Pydantic result, including stripping markdown code fences
- Return a clear error when the output is not valid JSON or is missing keys

### T3 Tests for the parser
- After T2. Cover valid JSON, fenced JSON, missing keys, wrong types, "Unknown" family, non-JSON text

### T4 Real image check
- Run `/detect` against a plain screenshot of typed text and against the stylized test image. Record the results.
- Decide whether to add the stylized-lettering line to the prompt

### T5 Write `index.html`
- File input, `fetch` to `/detect`, render the result, show errors and a loading state for the cold start
- A short note that images are sent to Google's Gemini API

### T6 Deploy (Leo does)
- Backend to Render with `GEMINI_API_KEY` set in the dashboard, frontend to GitHub Pages, point `index.html` at the Render URL

### T7 Update README
- Python backend setup, `/detect` request and response shape, limitations, privacy note

## Done
- Gemini API key created on the free tier
- `test.py` works end to end with `gemini-3.8-flash`
- API key moved into `.env`, and `.env` is gitignored
- Prompt chosen
- T1 Scaffold the FastAPI backend (see `progress.md`): 9 upload validation tests pass
