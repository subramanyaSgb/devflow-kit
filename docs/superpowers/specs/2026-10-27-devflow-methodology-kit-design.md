# devflow — Portable Development-Methodology Kit

**Status:** DRAFT (awaiting user review)
**Date:** 2026-10-27
**Author:** Kiran Hegde / Subramanya (Deevia) with Claude

## 1. Purpose

Extract the proven development discipline built up in the **HMD Standalone** project into a
single, reusable **Claude Code plugin** named `devflow`, so any new or existing project can adopt
the same workflow without hand-copying files.

The HMD practices being generalized:

- **Zero-context-loss session handoffs** — `/save_work` (snapshot + exhaustive stale-data sweep +
  `HANDOFF.md` resume contract) and `/continue_work` (resume exactly where the last session stopped).
- **Committed development log** — a `docs/devlog/` structure (decisions, sessions, per-phase
  task folders with brief / report / review / diff / test-run) committed *with* the work.
- **A Stop-hook guard** — blocks ending a turn until each "complete" subagent-driven task has its
  full committed devlog trail (test results are first-class artifacts).
- **CLAUDE.md as the operational source of truth** + lightweight project-memory discipline.
- **The superpowers loop** — brainstorm → write plan → subagent-driven implement → review →
  commit test artifacts.
- **Code-grounded documentation** — a "guidebook" / "demo guide" generator.

### Goal statement

> One sentence: *Make any project I open follow the HMD way of working — documented, resumable,
> reviewed, and test-evidenced — by installing one plugin and running one command.*

### Non-goals (YAGNI)

- No rigid config engine. The target project's **CLAUDE.md "Dev workflow (devflow)" section** *is*
  the configuration.
- No marketplace *publishing* in this iteration. The repo is structured so it *can* be published,
  but we ship local-install only.
- No modification of the HMD repo. (HMD may later drop its own local `devlog_guard.py` once it is
  on the plugin — a separate, optional step.)
- devflow does **not** reimplement superpowers. It orchestrates superpowers skills and adds the
  devlog / handoff / guard layer around them.

## 2. Delivery form — a Claude Code plugin + a bootstrap command

Chosen over a copy-a-template folder and over user-global config because: install once, improve
once, every project benefits; it versions cleanly; and it is shareable with teammates later.

### 2.1 Repository layout (`~/Desktop/devflow-kit/`, its own git repo)

```
devflow-kit/
├─ .claude-plugin/
│  ├─ plugin.json              # name: devflow, version 0.1.0, author, keywords
│  └─ marketplace.json         # lets: /plugin marketplace add ~/Desktop/devflow-kit → install devflow
├─ commands/
│  ├─ save-work.md             # generic port of HMD /save_work
│  ├─ continue-work.md         # generic port of HMD /continue_work
│  ├─ init-workflow.md         # the two-mode onboarding/bootstrap flow (§4)
│  ├─ document-feature.md      # guidebook, "page" generalized to "feature/module/surface"
│  └─ demo-guide.md            # client-facing walkthrough of a feature
├─ hooks/
│  ├─ hooks.json               # wires the Stop hook via ${CLAUDE_PLUGIN_ROOT}
│  └─ devlog_guard.py          # project-agnostic; reads $CLAUDE_PROJECT_DIR; fails open
├─ skills/
│  └─ devflow-method/
│     └─ SKILL.md              # connective tissue: the loop + when to use which command (§6)
├─ templates/                  # exact text init-workflow stamps into a target project
│  ├─ CLAUDE.md.tmpl           # full HMD-pattern CLAUDE.md (§5)
│  ├─ claude-devworkflow-section.md  # the "## Dev workflow (devflow)" block (appended to an existing CLAUDE.md)
│  ├─ devlog-README.md         # docs/devlog/ layout + status table
│  ├─ phase-README.md          # the per-task close-out checklist (per phase)
│  ├─ decisions.md             # seeded with decision 1: "adopted devflow"
│  ├─ HANDOFF.seed.md          # placeholder resume contract
│  └─ session.tmpl.md          # docs/devlog/sessions/YYYY-MM-DD.md starter
└─ README.md                   # what the plugin is, how to install, what each command does
```

Commands are invoked namespaced: `/devflow:save-work`, `/devflow:continue-work`,
`/devflow:init-workflow`, `/devflow:document-feature`, `/devflow:demo-guide`.

### 2.2 plugin.json / marketplace.json

`plugin.json`: `{ name: "devflow", version: "0.1.0", description, author, license: "MIT",
keywords: [workflow, devlog, handoff, tdd, documentation] }`.

`marketplace.json`: a one-plugin marketplace pointing at `.` so the user can add the local repo as
a marketplace and install `devflow` from it. Install path documented in the README:

```
/plugin marketplace add ~/Desktop/devflow-kit
/plugin install devflow@devflow-kit
```

## 2.3 What `/devflow:save-work` guarantees — the stale-data sweep

`save-work` is a faithful port of HMD's `/save_work`, preserving its hard rule verbatim:

> After save-work, **no living doc may contain a statement the current code/state contradicts.**

Behavior (every run, in order):

1. **Block on in-flight subagents** — if an implementer/reviewer Agent is still running, stop and
   tell the user to let it finish or cancel; a running agent's partial work cannot be frozen.
2. **Survey true state** — `git status`/`branch`/`log`; identify active phase, plan, spec, ledger,
   and the exact task + sub-step in progress; list background processes started and any stateful
   resource revision (e.g. DB migration).
3. **Preserve uncommitted work** — commit any dirty tree as `wip(save_work): …` with the project
   trailer; never `reset --hard` / `checkout --` / `clean` / `stash drop`.
4. **Exhaustive stale-data sweep (the core guarantee).** Not "update the file I was in." For every
   term the session **removed, renamed, re-pathed, re-scoped, or shipped**, grep it across every
   living doc and fix each hit. The living-doc set:
   - `CLAUDE.md` (goal, architecture, run/test, decisions table, dev-workflow section, any
     deployment/version line)
   - **project memory** + the `MEMORY.md` index (update status lines; fix/add/delete notes)
   - `docs/devlog/decisions.md`
   - spec/plan **status** (delivered → DELIVERED/LIVE; superseded → marked, never deleted)
   - `docs/guidebook/*`, `docs/demo-guide/*`
   - release / changelog / deploy / rollback notes
   - the active SDD ledger (`docs/devlog/<phase>/progress.md`)
   - the day's session file (`docs/devlog/sessions/<today>.md`)
   - **Portability note:** unlike HMD's hardcoded list, the generic command **discovers** the
     project's actual living docs — `CLAUDE.md`, everything under `docs/`, the memory dir, release
     notes, the ledger — and sweeps whatever it finds, so the guarantee holds for any project shape.
5. **Write the resume contract** → `docs/devlog/HANDOFF.md` (overwritten each time): timestamp,
   branch + HEAD, wip hash if any, active phase/plan/spec/ledger, the **single exact next action**,
   task-status snapshot, background processes to restart (exact commands), stateful revision, any
   open question, and the footer "run `/devflow:continue-work`".
6. **Commit + verify** — commit the handoff + doc updates; confirm `git status` is clean.
7. **Report** 3–5 lines: where things stand, the single next action, whether a wip commit was made.

Honest limits: the sweep is an LLM-driven discipline (same bar HMD runs at), not a formal proof;
and memory writes are best-effort — if the harness memory dir is unwritable, save-work updates
everything else and says so rather than failing.

## 3. The Stop-hook guard (the one piece of real code)

`hooks/devlog_guard.py` is the HMD guard, generalized:

- **Project root** comes from `$CLAUDE_PROJECT_DIR`; if unset, falls back to the current working
  directory. The script lives in the plugin, not the project, so it must never assume its own path
  is inside the repo.
- **Scratch ledger**: `<root>/.superpowers/sdd/progress.md` (the superpowers subagent-driven
  convention). If it or `<root>/docs/devlog/` is absent → **exit 0 (no-op)**. This is what keeps
  the globally-installed hook silently inert in any repo that has not been bootstrapped.
- **Phase directory**: read **only** from the ledger's `Devlog-dir:` line. HMD's `phaseN`-from-branch
  fallback is dropped (not portable). No `Devlog-dir:` → **fail open**.
- **Per completed task** (a `Task N: complete …` line in the ledger):
  - Always required (committed + git-tracked): `task-NN-report.md`, `task-NN-review.md`.
  - Normal tasks also require: `task-NN-brief.md`, `reviews/task-NN-r*.diff` (≥1),
    `tests/task-NN-tests.txt`.
  - **Close-out / controller** tasks (complete-line contains "close-out" or "controller") require
    report + review only.
  - Task numbers may be `NN` or `N`; the guard checks both spellings for tolerance.
- On any gap: print `{"decision":"block","reason": "<which files, which phase dir>"}` and exit 0,
  listing exactly what to mirror + commit.
- **Fails open (exit 0) on every unexpected error** — a bug in the guard can never wedge a session.
- Respects `stop_hook_active` so it never loops.

`hooks.json` wires it as a `Stop` hook. Invocation must be Windows-first (the primary environment)
and also work on POSIX:

```json
{ "hooks": { "Stop": [ { "hooks": [ {
  "type": "command",
  "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/devlog_guard.py\"",
  "timeout": 30,
  "statusMessage": "Checking devlog trail is committed"
} ] } ] } }
```

The guard is pure Python standard library (no third-party imports), so `python` on PATH is the only
requirement. If a project uses `py`/`python3`, that is a documented README note; the default assumes
`python` (true on the target Windows box). The guard shells out to `git ls-files` to test tracking,
exactly as HMD's does.

## 4. `/devflow:init-workflow` — two-mode onboarding

A Claude-driven command (markdown instructions). On run:

1. **Detect & confirm mode.** Heuristic: source files / a populated git history / a package
   manifest (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, …) ⇒ likely **existing**;
   otherwise **new**. Always *confirm* with the user rather than assume.
2. **Idempotency first.** If devflow is already initialized here (a "Dev workflow (devflow)" section
   in CLAUDE.md or a `docs/devlog/README.md` exists), report what is present and only fill gaps —
   never overwrite.

### 4.1 Existing project → "onboard"

1. **Frame** — ask what the project is and what kind (1–2 questions).
2. **Read the code** — explore structure, languages/frameworks, entry points, run story, test
   story, key modules, external integrations, obvious landmines. Use the `Explore` agent for broad
   fan-out and read manifests/config directly. Summarize findings back to the user.
3. **Clarify, one question at a time** — only what the code cannot answer: domain vocabulary,
   exact run/test commands, deploy story, conventions, known gotchas, the commit-trailer attribution.
4. **Generate the grounded trail:**
   - A rich **CLAUDE.md** in the HMD pattern (§5), filled from findings + answers. If a CLAUDE.md
     already exists, *enrich* it (append the Dev-workflow section + any missing standard sections)
     rather than replace it.
   - `docs/devlog/` scaffold: `README.md` (layout + status table), `decisions.md` (seed decision 1:
     "Adopted devflow workflow"), `sessions/<today>.md` (onboarding summary), `HANDOFF.md` seed.
   - **Best-effort** project-memory seed: a short project-overview note (and `MEMORY.md` index line)
     in the harness project-memory dir if writable; skipped silently if not.
5. **Report** — what was found, what was created, and the exact next action (usually: "run
   `/devflow:save-work` whenever you pause, and start work via `superpowers:brainstorming`").

### 4.2 New project → "greenfield"

1. **Ask what you want to build** (short intake — enough to name the project and its goal).
2. Scaffold `docs/devlog/`, a **CLAUDE.md skeleton** (goal + the standard sections, marked to grow),
   `decisions.md` seed, `sessions/<today>.md`, `HANDOFF.md` seed, memory seed (best-effort).
3. **Hand into the superpowers loop** — invoke `superpowers:brainstorming` to design the first
   feature, which terminates in `writing-plans`, then subagent-driven implementation. From task 1
   the devlog trail + guard are active.

Both modes converge on the same end-state: save-work / continue-work / guard / devlog all live.

## 5. The generated CLAUDE.md pattern

Templated from HMD's structure so every devflow project carries the same backbone:

- **Title + one-sentence goal** + link to the main spec (once one exists).
- **HARD RULE: full development documentation** — the devlog discipline, the per-task close-out
  checklist (brief / report / review / diff / tests), the guard, "never delete docs, mark superseded".
- **Working rules** — greenfield vs existing; verify against reality before assuming; **ask when in
  doubt**; never commit secrets or client data.
- **Decisions table** — seeded; appended as decisions are made.
- **Architecture / How to run / Tests** — filled from code (existing) or skeleton (new).
- **Dev workflow (devflow)** — the machine-read contract (see §5.1).
- **Open questions** — to confirm during build.

### 5.1 The "Dev workflow (devflow)" contract section

A small, stable block that the generic commands read so they need no HMD specifics:

| Field | Meaning | Used by |
|---|---|---|
| `Commit trailer` | the `Co-Authored-By:` line to end commits with | save-work |
| `Run commands` | how to start the app / long-running processes (if any) | continue-work |
| `Restart commands` | the exact commands to restart those processes in a fresh session | continue-work |
| `Test command` | the project's test entry point(s) | save-work, continue-work, verification |
| `Stateful resources` | e.g. a DB migration revision to confirm (if any) | save-work, continue-work |
| `Scratch ledger` | path of the SDD ledger (default `.superpowers/sdd/progress.md`) | guard, save-work |

For a library/CLI with no long-running processes, Run/Restart/Stateful are "none" and
continue-work simply skips the process-restart step.

## 6. `devflow-method` skill — the connective tissue

A skill that triggers when starting substantive work in a devflow project (a repo with the
Dev-workflow section / `docs/devlog/`). It:

- States the loop: **brainstorm → plan → subagent-driven implement (with per-task devlog trail) →
  review → commit test artifacts → save/continue at session boundaries.**
- Defers the *how* of each step to the matching superpowers skill (brainstorming, writing-plans,
  subagent-driven-development, requesting-code-review, test-driven-development).
- Points at the five devflow commands and the guard's requirements.
- Stays light — a reminder + router, not a wall of rules. It must not fight superpowers' own
  skill-priority rules.

## 7. Generalized documentation commands

- **`/devflow:document-feature <name>`** — HMD's guidebook flow with "page" reframed as
  "feature / module / surface": discuss grounded in code → fix issues with permission → write
  `docs/guidebook/<name>.md`.
- **`/devflow:demo-guide <name>`** — client/stakeholder-facing walkthrough of a feature →
  `docs/demo-guide/<name>.md`. Documentation only; never changes app code.

## 8. Build order (for the implementation plan)

1. Plugin skeleton: `.claude-plugin/plugin.json` + `marketplace.json` + `README.md`.
2. Generic guard: `hooks/devlog_guard.py` + `hooks/hooks.json` (the one code unit — TDD it).
3. Commands: `save-work.md`, `continue-work.md` (generic ports reading the §5.1 contract).
4. `templates/*` (CLAUDE.md.tmpl, devlog-README, phase-README, decisions, HANDOFF, session).
5. `init-workflow.md` (two-mode; depends on templates existing).
6. `document-feature.md`, `demo-guide.md`.
7. `skills/devflow-method/SKILL.md`.
8. README + local-install + verification pass.

## 9. Verification plan

- **Install:** `/plugin marketplace add ~/Desktop/devflow-kit` then `/plugin install devflow@devflow-kit`;
  confirm the five commands and the skill appear.
- **Guard fail-open:** in a throwaway repo with no `docs/devlog/` and no SDD ledger, confirm ending a
  turn is never blocked.
- **Guard block-then-pass:** in a repo with an SDD ledger marking a task complete but missing its
  trail, confirm the Stop hook blocks with the precise file list; add the files + commit; confirm it
  passes. Repeat for a `controller` task (report + review only).
- **init-workflow (new):** run in an empty dir → confirm CLAUDE.md skeleton + `docs/devlog/` +
  seeds are created, non-destructively, and that it routes into brainstorming.
- **init-workflow (existing):** run in a small existing repo → confirm it reads the code, asks
  sensible clarifying questions, and produces a grounded CLAUDE.md + scaffold without clobbering an
  existing CLAUDE.md.
- **save-work / continue-work round-trip:** in a bootstrapped repo, make a half-done change, run
  save-work (confirm clean tree + HANDOFF.md written), then continue-work (confirm it resumes from
  the HANDOFF).
- **The guard's own test:** a pytest for `devlog_guard.py` covering no-ledger, missing `Devlog-dir:`,
  a normal task missing each required file, a controller task, and the all-present pass case.

## 10. Open questions (confirm during build)

- Exact plugin + command names final? (`devflow`, `/devflow:save-work`, …)
- Should `document-feature` / `demo-guide` be included from the start, or deferred until after the
  core loop is proven? (Spec includes them; easy to defer in the plan.)
- Memory seeding: acceptable as best-effort-and-skip, or must it be guaranteed?
- Default commit-trailer attribution when the user gives none at init time (follow the session's
  attribution, or leave a clearly-marked placeholder)?
