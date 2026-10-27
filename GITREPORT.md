# GITREPORT.md

A plain-language log of every commit, oldest first. New commits go at the bottom.

**Branch vs Task:** the Branch column is the real git branch name, exactly as `git branch` and `git log` show it. The Task column is only a reading aid: it says which task in `TASKS.md` the commit or branch belongs to. Task labels use the IDs from `TASKS.md` (T1, T2, T3, T3b, T4). `Setup` means project housekeeping that belongs to no task. A commit is labelled by the task it serves, so it can differ from the branch it was made on.

This file is tracked in git, starting with the commit that added it.

## Insturction
Add the row in the same commit it describes (merges included). A commit cannot know its own hash, so write `(pending)` in the Hash column. Whoever adds the next row first replaces the previous `(pending)` with the real hash from `git log --oneline -2`.

```
| Date | Hash | Branch | Task | Commit message | What changed, in plain words |
```

## Branches right now (2026-10-27, after the T5b merge)

| Branch | Task | Points to | State |
|---|---|---|---|
| `main` | T1 to T5b | `407b08c` T5b | 15 commits ahead of GitHub (`origin/main` is at `2e5afde`). Not pushed. |
| `t5c` | T5c | latest row in the log | Google Fonts search link on the font name and alternative chips in `index.html`. In use. Not merged into `main` yet. |
| `t5b` | T5b | `407b08c` T5b | Fully merged into `main` (fast-forward). Safe to delete. |
| `t4b-prompt-timeout` | T4, T4b | `e4e0f57` T4b | Fully merged into `main` (fast-forward). Safe to delete. |
| `t5-frontend` | T5 | `e93f1d8` T5 | Fully merged into `main` (fast-forward). Safe to delete. |
| `t4-real-check` | T4 | `10a8c35` T4 | Fully merged into `main`. Replaced by `t4b-prompt-timeout`. Safe to delete. |
| `fix-upload-limit` | T3b | `6b22f2d` T3b | Fully merged into `main`. Safe to delete. |
| `t3-test` | T2, T3 | `2e5afde` | Fully merged into `main`. Safe to delete. |
| `claude` | T1 | `5f0adf4` | Fully merged into `main`. Safe to delete. |

## Commit log

| Date | Hash | Branch | Task | Commit message | What changed, in plain words |
|---|---|---|---|---|---|
| 2026-10-17 | `6a3bf26` | main | Setup | first commit | Project start: `.gitignore`, `ReadMe.md`, `TASKS.md`, `test.py`. |
| 2026-10-17 | `0c71f8b` | main | Setup | Add .claude/settings.json to .gitignore | Keeps Claude's permission file out of git. |
| 2026-10-18 | `b5a4b26` | claude | T1 | Task 1 | T1 backend: `backend/main.py`, upload tests, `requirements.txt`, `.env.example`, `progress.md`. Also added `text.png` and `todo.txt` by mistake. |
| 2026-10-18 | `5f0adf4` | claude | T1 | Task 1 Remove unused files | Removed `text.png` and `todo.txt`. They are still in history and on GitHub. |
| 2026-10-19 | `a4359a9` | t3-test | T2 | Implement T2: Parse and validate the Gemini response | T2 parser in `main.py`. Written while on `main` by mistake, then moved to `t3-test` before committing. |
| 2026-10-19 | `ac1a204` | t3-test | T3 | Update TASKS.md: Adjust task references and clarify T3 tests for the parser | Task list updated for T3. |
| 2026-10-19 | `d263dea` | t3-test | T3 | Add T3 tests for parse_gemini_response() and update validation logic | `progress.md` T3 notes only, despite the message. |
| 2026-10-19 | `c5b29d3` | t3-test | T3 | Add validation for empty font family in parse_gemini_response() | Parser now rejects an empty `family`. |
| 2026-10-19 | `2e5afde` | t3-test | T3 | Add comprehensive tests for parse_gemini_response() including valid and invalid cases | New `backend/tests/test_parser.py`. `main` was moved up to here and pushed to GitHub. |
| 2026-10-19 | `044ef96` | t4-real-check | Setup | minor change | Moved `test.py` to `refrence/test.py` (folder name misspelled). Not in `main` yet. |
| 2026-10-20 | `71750e8` | t4-real-check | T4 | Update .gitignore to include samples/ and add ISSUES.md for tracking project issues | Ignores `samples/`, adds `ISSUES.md`. |
| 2026-10-20 | `c1942d5` | fix-upload-limit | T3b | Add ISSUES.md | Same `ISSUES.md` added on the fix branch. This is why the later merge conflicted. |
| 2026-10-20 | `960f66a` | fix-upload-limit | T4 | git ignore forgot on t4 | `.gitignore` change copied from T4. |
| 2026-10-20 | `39af8f6` | fix-upload-limit | T4 | git ignore forgot on t4 (spelling wrong) | Fixed a typo in that `.gitignore` line. |
| 2026-10-20 | `6b22f2d` | fix-upload-limit | T3b | T3b: Implement upload size limit fix with BodySizeLimitMiddleware and update related tests (Issue Fix) | 1 MiB upload limit and byte-counting middleware, 5 new tests, docs. Then `main` was moved up to here. |
| 2026-10-20 | `cd8776b` | t4-real-check | T4 | Merge branch 'main' into t4-real-check | Brought the T3b fix into T4. `ISSUES.md` conflicted (added on both branches) and was resolved by keeping `main`'s version. |
| 2026-10-20 | `9a209df` | t4-real-check | Setup | Add GITREPORT.md | Adds this report. Every commit from here on adds its own row. |
| 2026-10-20 | `10a8c35` | t4-real-check | T4 | Update documantation for T4 Issue: Continue to T5 | Docs only. Fixed this report's last row and branch table, added the T4 failure entry to `ISSUES.md` (Gemini 503/504), a "T4 paused" section in `progress.md`, and the T4 and T6 notes in `TASKS.md`. Then `main` was moved up to here. |
| 2026-10-20 | `f790722` | t5-frontend | T5 | Update TASKS.md and progress.md for T5: Add `index.html` task details and document implementation progress | Docs only. T5 moved to Done in `TASKS.md` and a T5 section added to `progress.md`. The page itself came in the next commit. |
| 2026-10-22 | `d665250` | t5-frontend | T5 | T5: Front End Add index.html for font detection functionality with image upload and API integration | New `index.html` at the repo root: file picker with preview, type and 1 MiB check before upload, loading message, result card, error messages. Checked with a stubbed `fetch` and by hand against the real backend. |
| 2026-10-22 | `e93f1d8` | t5-frontend | T5 | T5: Front End Update GITREPORT.md | Report only. Rows for `10a8c35`, `f790722`, `d665250` and a new branch table. Then `t5-frontend` was merged into `main` (fast-forward, no merge commit). |
| 2026-10-23 | `4b9b9f0` | t4b-prompt-timeout | T4 | T4: Raise Gemini timeout to 60 s and rewrite the prompt for accuracy | `backend/main.py`: timeout 30 to 60 s, new prompt (no "prefer well-known names", letterform checklist, Google Fonts in scope, stricter "high" confidence). Same keys, parser untouched. `progress.md` T4 retry section: old-prompt accuracy table, first new-prompt results (Playfair right, JetBrains Mono wrong), category right 7 of 8, 503 pattern and the 3-try test rule. `ISSUES.md`: timeout update and new wrong-font issue. `TASKS.md`: T7 must list the Gemini API limitations. |

| 2026-10-23 | `e4e0f57` | t4b-prompt-timeout | T4b | T4b: Implement Gemini model fallback with multiple timeouts and logging | `backend/main.py`: one `MODELS` list replaces the single model and timeout. `call_gemini()` tries `gemini-3-flash-preview` (40 s), then `gemini-3.5-flash-lite` (20 s), then `gemini-3.1-flash-lite` (20 s) on 503, 429, timeout or other 5xx, and logs which model answered. New `backend/tests/test_gemini_fallback.py` (17 tests, 61 pass). `progress.md` T4b section with the real 5-image run (no 503, family 2 of 5, category 4 of 5), `ISSUES.md` and `TASKS.md` updated. |
| 2026-10-27 | `407b08c` | t5b | T5b | T5b: Revamp index.html layout: category first, paste and drag and drop, progress timer, reset, dark mode | `index.html`: result card leads with the category, family shown as a best guess with alternatives, confidence kept. Removed the "Why" field, the intro line and the accuracy note; privacy note moved to a footer. Paste and drag and drop go through the same file checks as the picker. "Working, 12 s" progress with a "may be busy" hint after 20 s. "Try another image" reset. Dark mode with CSS variables. Backend untouched. `TASKS.md` adds T5c, T5d, T5e. `progress.md` and `ISSUES.md` updated. |
| 2026-10-27 | `(pending)` | t5c | T5c | T5c: Link the font name and alternatives to a Google Fonts search | `index.html`: the best-guess name itself links to a Google Fonts search (highlighted), alternatives as link chips. All links come from one function: fixed `https://fonts.google.com/?query=` plus `encodeURIComponent`. No link when the family is "Unknown". A Copy button was tried and removed. Also Leo's T5b full stop fix in the progress text. `progress.md` T5c section and T5b wording, `TASKS.md` updated. |
