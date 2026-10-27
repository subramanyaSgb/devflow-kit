# Development Log

**Hard rule:** every plan, test case, test result, review and decision is recorded here and
committed with the work. Nothing in `docs/` is deleted; superseded material is marked, not removed.

## Layout

| Path | Holds |
|---|---|
| `decisions.md` | Every product/technical decision: date, who, why |
| `HANDOFF.md` | Living resume pointer, overwritten by `/devflow:save-work` |
| `sessions/YYYY-MM-DD.md` | What happened each session |
| `<phase>/progress.md` | Task ledger (status, commit range, review verdict) |
| `<phase>/README.md` | The per-task close-out checklist |
| `<phase>/task-NN-brief.md` | The task text given to the implementer |
| `<phase>/task-NN-report.md` | Implementer report + TDD evidence + fix rounds |
| `<phase>/task-NN-review.md` | Reviewer verdict, every round |
| `<phase>/reviews/task-NN-rN.diff` | The exact diff each review looked at |
| `<phase>/tests/task-NN-tests.txt` | The real failing→passing test run (first-class artifact) |

The scratch ledger `.superpowers/sdd/progress.md` must carry a `Devlog-dir: docs/devlog/<phase>`
line so the Stop-hook guard tracks the right phase.
