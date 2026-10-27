---
description: Snapshot work, sweep every living doc for stale data, write HANDOFF before /clear
---

Produce a COMPLETE, loss-less handoff so a fresh session resumes at the exact same point.
Hard checklist — do every step in order; the bar is "no information missed, no stale data."

Read the project's `CLAUDE.md` "Dev workflow (devflow)" block first for the **commit trailer**,
**push policy**, **restart commands**, **stateful resources**, and **scratch ledger** path. Use
those values throughout. If a field is missing, note it and proceed.

## 1. Block on in-flight subagents
If any Agent/Task you dispatched is still running, STOP and tell the user to let it finish or
cancel — a running agent's partial work cannot be frozen.

## 2. Survey true state
`git status --short`, `git branch --show-current`, `git log --oneline -6`. Identify the active
phase, plan, spec, ledger, and the **exact task + sub-step** in progress (specific, not "Task 4"
but "Task 4 implemented, review not run" etc.). List background processes started and any stateful
revision (from the contract).

## 3. Preserve uncommitted work
- Dirty tree → stage and commit as `wip(save_work): <one line>` with the contract's commit trailer;
  record the hash. **Secret safety:** before staging, respect `.gitignore` and check for `.env`/key
  files/high-entropy tokens — if any would be staged, pause and ask.
- Clean tree → note "tree clean, no WIP".
- Never `git reset --hard` / `checkout --` / `clean` / `stash drop`.
- Not a git repo / detached HEAD / mid-merge → stop and say so; still write HANDOFF (step 5).

## 4. Exhaustive stale-data sweep (the core guarantee)
After save-work, **no living doc may contradict the current code/state.** For every term the
session **removed, renamed, re-pathed, re-scoped, or shipped**, grep it across every living doc and
fix each hit. Discover the project's actual living docs — don't assume a fixed list:
- `CLAUDE.md` (goal, architecture, run/test, decisions table, dev-workflow block, any version line)
- project memory + its index, if present (best-effort)
- `docs/devlog/decisions.md`
- spec/plan **status** (delivered → DELIVERED/LIVE; superseded → marked, never deleted)
- `docs/guidebook/*`, `docs/demo-guide/*`
- release / changelog / deploy / rollback notes
- the active ledger `docs/devlog/<phase>/progress.md`
- the day's session file `docs/devlog/sessions/<today>.md` (append, don't overwrite)
The bar is "no stale data anywhere," not "I updated the obvious file."

## 5. Write the resume contract → `docs/devlog/HANDOFF.md` (overwrite)
Use the labelled schema: Timestamp, Branch, HEAD, WIP-commit (hash/none), Phase, Plan, Spec,
Ledger, **Next-action** (one concrete executable step — never vague), Task-status, Restart (exact
commands/none), Stateful (revision/none), Open-question (or none), and the footer
`Resume with: /devflow:continue-work`.

## 6. Commit and verify
Commit the handoff + doc updates as `docs(handoff): save_work snapshot — <phase/task>` with the
trailer. Confirm `git status --short` is empty. Push only if the contract's push policy names a
remote and it is reachable; otherwise note "not pushed".

## 7. Report (3–5 lines)
Where things stand, the single next action, whether a WIP commit was made, then:
"Ready to `/clear`. In the new session, run `/devflow:continue-work`."
