# <phase> — close-out checklist

Run EVERY task, as soon as its review is clean, before dispatching the next:

1. Copy `task-NN-brief.md`, `task-NN-report.md` (with every fix round), `task-NN-review.md`
   (verdict for every round), `reviews/task-NN-rN.diff`, and `tests/task-NN-tests.txt`
   (failing→passing) from scratch into this dir.
2. Update `progress.md` (status → complete, commit range, verdict) and the scratch ledger.
3. `git add` those devlog files and commit them with (or right after) the task's code commit.
4. Close-out/controller tasks need only report + review.

At phase end: add `final-review.md`, `reviews/final-branch-review.diff`, and a full-suite
`tests/full-suite-<date>.txt`.
