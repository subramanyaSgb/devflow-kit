---
description: Resume work exactly where the last session left off, from HANDOFF — zero context loss
---

Resume from the saved handoff with zero context loss. Hard checklist — every step in order.

## 1. Read the resume contract
Read `docs/devlog/HANDOFF.md`. If it is absent, empty, or its Timestamp is far behind the latest
commit, say so and ask the user where to resume — do NOT guess.

## 2. Load the context it points to
CLAUDE.md + any project memory are auto-loaded. Read the active ledger
(`docs/devlog/<phase>/progress.md`), the plan, and the spec the handoff names. If a task is
mid-flight, read its brief/report/review.

## 3. Verify git state matches
`git branch --show-current`, `git log --oneline -6`. Branch must match. HEAD should be the handoff's
noted commit or a later commit on the same branch. Flag ONLY if the branch differs or history
rewound below the noted commit. If a `wip(save_work)` commit is at HEAD and the handoff says the
task needs more edits → `git reset --soft HEAD~1` to restore the WIP to the working tree.

## 4. Re-establish the environment
Restart the background processes from the contract's **Restart commands** (run in background).
Confirm any **Stateful** revision (e.g. a migration) matches; apply it if the handoff says to.
**If a restart command fails, report the failing command and continue with the rest — do not loop.**

## 5. Reconcile reality with the handoff
Run the quickest proof (a named test / a commit exists). If a check contradicts the handoff, STOP
and surface the specific mismatch before proceeding.

## 6. Execute the EXACT NEXT ACTION
Do the single next action from the handoff, then continue the normal loop (implement → review →
fix → update ledger per task). Keep going autonomously; stop only for a genuine blocker or a
user decision.

## 7. First, report (2–3 lines)
"Resuming: <phase>/<task>. State: <one line>. Next action: <X>." Then proceed.
