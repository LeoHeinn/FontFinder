# GITREPORT.md

A plain-language log of every commit, oldest first. New commits go at the bottom.

**Branch vs Task:** the Branch column is the real git branch name, exactly as `git branch` and `git log` show it. The Task column is only a reading aid: it says which task in `TASKS.md` the commit or branch belongs to. Task labels use the IDs from `TASKS.md` (T1, T2, T3, T3b, T4). `Setup` means project housekeeping that belongs to no task. A commit is labelled by the task it serves, so it can differ from the branch it was made on.

This file is tracked in git, starting with the commit that added it.

## Insturction
Add the row in the same commit it describes (merges included). A commit cannot know its own hash, so write `(pending)` in the Hash column. Whoever adds the next row first replaces the previous `(pending)` with the real hash from `git log --oneline -2`.

```
| Date | Hash | Branch | Task | Commit message | What changed, in plain words |
```

## Branches right now (2026-10-22)

| Branch | Task | Points to | State |
|---|---|---|---|
| `main` | T1 to T3b, T4 notes | `10a8c35` T4 | 9 commits ahead of GitHub (`origin/main` is at `2e5afde`). Not pushed. |
| `t5-frontend` | T5 | `d665250` T5 | 2 commits ahead of `main` (`f790722`, `d665250`). Not merged into `main` yet. |
| `t4-real-check` | T4 | `10a8c35` T4 | Fully merged into `main`. T4 is paused (Gemini 503/504 and wrong fonts). Retry on this branch or a new one. |
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

