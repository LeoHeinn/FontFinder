# TASKS.md

Only one task is "In progress" at a time. 

## In progress

### T1 Scaffold the FastAPI backend
- `backend/main.py` with `POST /detect` accepting one uploaded image (multipart form)
- Reject anything that is not PNG, JPEG or WebP, or is over the size limit, before calling Gemini. Agree the limit with Leo in the plan.
- Call Gemini with the prompt from `AGENTS.md`, key read from `GEMINI_API_KEY`
- Pydantic response model matching the prompt's keys
- Call `parse_gemini_response()` as a stub that raises `NotImplementedError`. Leo writes it in T2.
- CORS middleware
- Gemini 503, 429 and timeouts return clear HTTP errors
- `backend/requirements.txt` and `.env.example`
- Done when: the app imports cleanly, pytest tests for upload validation pass, and Leo has approved the plan

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
