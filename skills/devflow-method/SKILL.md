---
name: devflow-method
description: Use when starting substantive work in a devflow project (a repo with a docs/devlog/ trail or a "Dev workflow (devflow)" section in CLAUDE.md) — establishes the loop and routes to the right command/skill.
---

# devflow method

This project follows **devflow**. Work in this loop:

1. **Brainstorm** a change → `superpowers:brainstorming` (design + spec before code).
2. **Plan** → `superpowers:writing-plans` (task-by-task).
3. **Implement** → `superpowers:subagent-driven-development`, writing the per-task devlog trail
   (brief / report / review / reviews/*.diff / tests/*.txt) and committing it with each task.
4. **Review** → `superpowers:requesting-code-review` between tasks.
5. **Test-evidence** → commit `tests/task-NN-tests.txt` (failing→passing) per task.
6. **Session boundaries** → `/devflow:save-work` before `/clear`; `/devflow:continue-work` to resume.

The Stop-hook guard blocks ending a turn until each `complete` task has its committed trail
(close-out/controller tasks: report + review only).

**This skill is a router, not a rulebook** — defer the *how* of each step to the named superpowers
skill, and follow normal skill-priority. If the superpowers plugin is not installed, proceed with a
minimal inline brainstorm→plan→build and tell the user superpowers would add the full loop.
