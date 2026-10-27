# devflow

A portable Claude Code plugin that gives any project the HMD development workflow:
save/continue session handoffs, a committed `docs/devlog/` trail, a fail-open Stop-hook
guard that enforces it, and a one-command project bootstrap.

## Install (local)

```
/plugin marketplace add ~/Desktop/devflow-kit
/plugin install devflow@devflow-kit
```

## Commands

| Command | What it does |
|---|---|
| `/devflow:init-workflow` | Bootstrap this repo — onboard an existing codebase or start a greenfield project |
| `/devflow:save-work` | Snapshot work, sweep every living doc for stale data, write `HANDOFF.md` before `/clear` |
| `/devflow:continue-work` | Resume exactly where the last session stopped, from `HANDOFF.md` |
| `/devflow:document-feature <name>` | Write a code-grounded guidebook for a feature/module |
| `/devflow:demo-guide <name>` | Write a client-facing walkthrough of a feature |

The Stop-hook guard activates only in a repo that has `docs/devlog/` + an SDD ledger; it is a
silent no-op everywhere else. Optional per-project config: `.devflow/guard.json`.

See `docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md` for the full design.
