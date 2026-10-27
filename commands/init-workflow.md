---
description: Bootstrap this repo for devflow — onboard an existing codebase or start greenfield
---

Set up (or refresh) the devflow workflow in the current repository. The plugin's templates are at
`${CLAUDE_PLUGIN_ROOT}/templates/`. Be non-destructive and idempotent: safe to re-run.

## 0. Fix the project root
Resolve the root as `git rev-parse --show-toplevel` (or the current dir if not a repo). In a
monorepo, confirm with the user whether they mean the repo root or a sub-package. Never write
outside the chosen root.

## 1. Detect & confirm mode
Heuristic: source files / populated git history / a manifest (`package.json`, `pyproject.toml`,
`go.mod`, `Cargo.toml`, …) ⇒ likely **existing**; otherwise **new**. Always confirm with the user.

## 2. Idempotency / refresh
If a `devflow:` marker already exists in `CLAUDE.md` or `docs/devlog/README.md` exists → **refresh
mode**: report what is present, offer to update managed marker-sections in place (only the bytes
between a matching begin/end pair), and create only what is missing. Never overwrite user content.

## 3. Pre-flight
List every path you will create or touch and show it to the user before writing anything.

## EXISTING → onboard
1. Ask what the project is and what kind (1–2 questions).
2. Read the code **bounded**: structure, languages/frameworks, entry points, run story, test story,
   key modules, integrations, landmines. Use the `Explore` agent for fan-out; read
   manifests/config/CI directly; sample, don't read every file. Summarize findings back for
   correction before writing.
3. Clarify, one question at a time — only what the code can't answer: domain terms, exact run/test
   commands, deploy story, conventions, gotchas, the commit-trailer attribution.
4. Generate the grounded trail (each managed section wrapped in `devflow:*` markers from templates):
   - Fill `CLAUDE.md` from `templates/CLAUDE.md.tmpl` + `claude-devworkflow-section.md`, substituting
     project name/goal/architecture/run/test/trailer from findings + answers. If a CLAUDE.md exists,
     insert only the marker-sections and leave the rest byte-for-byte.
   - Scaffold `docs/devlog/`: `README.md` (from template), `decisions.md` (seed decision 1 with
     today's date), `sessions/<today>.md`, `HANDOFF.md` (from seed). Create `<phase>/` lazily when
     work starts.
   - Best-effort project-memory seed (skip silently if the memory dir is unwritable).
   - Add `.devflow/` to `.gitignore` (the guard's debug log lives there). If the user wants
     project-wide guard config committed, also add a negation so only that one file is tracked:
     ```
     .devflow/
     !/.devflow/guard.json
     ```
5. Report findings + what was created + the next action
   ("run `/devflow:save-work` to pause; start work via `superpowers:brainstorming`").

## NEW → greenfield
1. Ask what the user wants to build (enough to name the project + its goal).
2. Scaffold `docs/devlog/` + a `CLAUDE.md` skeleton (goal + standard sections, marked to grow) +
   `decisions.md` seed + `sessions/<today>.md` + `HANDOFF.md` seed + best-effort memory seed.
3. Hand into the superpowers loop: invoke `superpowers:brainstorming` for the first feature (→
   `writing-plans` → subagent-driven implementation). From task 1 the devlog trail + guard are live.
   **If the superpowers plugin is not installed**, say so, point the user at installing it, and fall
   back to a minimal inline brainstorm→plan→build outline so work still proceeds.

Both modes converge: save-work / continue-work / guard / devlog all live.
