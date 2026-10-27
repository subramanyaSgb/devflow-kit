# devflow — Portable Development-Methodology Kit

**Status:** FINAL — all open questions resolved (§17); approved to proceed to the implementation plan (2026-10-27)
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
│  ├─ run-guard.cmd            # Windows launcher: finds a Python, runs the guard
│  ├─ run-guard.sh             # POSIX launcher: finds a Python, runs the guard
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
│  ├─ guard.json               # OPTIONAL per-project guard config (defaults baked in; §3.1)
│  └─ session.tmpl.md          # docs/devlog/sessions/YYYY-MM-DD.md starter
├─ tests/
│  └─ test_devlog_guard.py     # pytest for the guard (the one unit-testable component)
└─ README.md                   # what the plugin is, how to install, what each command does
```

All files `init-workflow` stamps into a project are wrapped in idempotency markers
(`<!-- devflow:begin <id> -->` … `<!-- devflow:end <id> -->`) so a re-run can refresh a managed
section in place without clobbering the user's own edits around it (§4.2).

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

### 2.3 What `/devflow:save-work` guarantees — the stale-data sweep

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

**Cross-platform launch (robustness).** The hook does not call `python` directly — a bare `python`
is absent or is Python 2 on many machines. Instead `hooks.json` calls a thin platform launcher that
locates a working Python 3 and execs the guard:

```json
{ "hooks": { "Stop": [ { "hooks": [ {
  "type": "command",
  "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-guard.cmd\"",
  "timeout": 30,
  "statusMessage": "Checking devlog trail is committed"
} ] } ] } }
```

- `run-guard.cmd` (Windows) tries, in order, `py -3`, `python`, `python3`; the first that resolves
  runs `devlog_guard.py`. If none resolves, it exits 0 (fail open — never block over a missing
  interpreter).
- `run-guard.sh` (POSIX) does the same with `python3` then `python`. A companion POSIX entry can be
  added to `hooks.json` for mac/Linux users; on the target Windows box only the `.cmd` is needed.
- The guard itself is **pure Python standard library** (no third-party imports) so no environment
  setup is ever required.

**Committed, not merely staged.** The guard tests a file with `git ls-files --error-unmatch`
(tracked) *and* `git log -1 --format=%H -- <path>` returns non-empty (it exists in history). A file
that is only `git add`-ed but never committed therefore does **not** satisfy the trail — matching the
rule's intent that the trail is *committed* with the work. Any git error → fail open.

### 3.1 Optional per-project guard config

Zero config is required — the defaults below are baked into the script and match HMD exactly. A
project that works differently may drop a `.devflow/guard.json` in its root to override, read once
per run (absent or unparseable → defaults, never an error):

```jsonc
{
  "scratch_ledger": ".superpowers/sdd/progress.md",   // where "Task N: complete" lines live
  "required_normal":  ["brief", "report", "review", "diff", "tests"],
  "required_closeout": ["report", "review"],
  "closeout_keywords": ["close-out", "closeout", "controller"],
  "enabled": true                                      // false → guard is a no-op for this repo
}
```

This makes the guard robust to projects that want a lighter trail (e.g. `report`+`review` only) or a
different ledger location, without forking the plugin. `enabled:false` is the clean per-project
off-switch (distinct from the global fail-open, which triggers only when the structure is absent).
Config is **data only** — the guard never evaluates or executes anything from `guard.json`; unknown
keys are ignored; values are type- and size-checked (lists of short strings, one small boolean/path).

### 3.2 Guard implementation notes (performance & debuggability)

- **Stay inside the 30 s timeout — batch, don't loop subprocesses.** The guard makes exactly
  **two** git calls total, not 2–5 per task: one `git ls-files -- <phase_dir>` (everything git
  tracks under the phase dir) and one `git ls-tree -r --name-only HEAD -- <phase_dir>` (everything
  committed in HEAD under it). Both results are read into Python sets; every per-task file check is
  then a set membership test. A task's file must appear in the **committed** set (HEAD), which
  subsumes the "committed, not merely staged" rule in one pass. Cost is O(1) git calls regardless of
  task count, so a 40-task phase is as fast as a 1-task phase.
- **Fail-open diagnostics.** On any unexpected exception the guard still exits 0, but when
  `DEVFLOW_GUARD_DEBUG=1` it appends a one-line reason (timestamp + exception) to
  `<root>/.devflow/guard.log`, so a "why didn't the guard fire?" question is answerable. With the
  env var unset it is completely silent — no file writes, no stderr noise.
- **Determinism.** Ledger parsing is a single pass of documented regexes (§11); task numbers are
  normalized to `NN`; duplicate `Task N` lines resolve to "complete if any line says complete".
- **Read-only.** The guard never writes to the repo (except the opt-in debug log under `.devflow/`,
  which `init-workflow` adds to `.gitignore`).

## 4. `/devflow:init-workflow` — two-mode onboarding

A Claude-driven command (markdown instructions). On run:

0. **Fix the project root.** Resolve the target root as the nearest enclosing git repo
   (`git rev-parse --show-toplevel`), or the current dir if none. In a monorepo, confirm whether the
   user means the repo root or a sub-package, and scaffold at the chosen root. Never write outside it.
1. **Detect & confirm mode.** Heuristic: source files / a populated git history / a package
   manifest (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, …) ⇒ likely **existing**;
   otherwise **new**. Always *confirm* with the user rather than assume.
2. **Idempotency first.** If devflow is already initialized here (a `devflow:*` marker in CLAUDE.md
   or a `docs/devlog/README.md` exists), switch to **refresh mode**: report what is present, offer to
   update managed marker-sections in place, and only create what is missing. Never overwrite a user's
   own content. `init-workflow` is therefore safe to re-run and doubles as a health check.
3. **Pre-flight & dry-run.** List every path it will create or touch and show it to the user before
   writing anything. If `git` is dirty with unrelated changes, note it; writes go to new files, so no
   existing work is at risk.

### 4.1 Existing project → "onboard"

1. **Frame** — ask what the project is and what kind (1–2 questions).
2. **Read the code (bounded).** Explore structure, languages/frameworks, entry points, run story,
   test story, key modules, external integrations, obvious landmines. Use the `Explore` agent for
   broad fan-out and read manifests/config/CI directly. **Bounded:** read breadth-first and sample —
   manifests, configs, entry points, READMEs, CI files, directory shape — not every source file;
   on a large repo, summarize per top-level area rather than exhaustively. Present findings back to
   the user for correction before writing anything (the user is the authority on intent, not the
   code alone).
3. **Clarify, one question at a time** — only what the code cannot answer: domain vocabulary,
   exact run/test commands, deploy story, conventions, known gotchas, the commit-trailer attribution.
4. **Generate the grounded trail** (each managed section wrapped in `devflow:*` markers):
   - A rich **CLAUDE.md** in the HMD pattern (§5), filled from findings + answers. If a CLAUDE.md
     already exists, insert only the managed marker-sections (Dev-workflow + any missing standard
     sections) into it and leave everything else byte-for-byte; never rewrite the user's prose.
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
| `Push policy` | whether/where to push after save-work (e.g. `origin <branch>`, or `none`) | save-work |
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
2. Generic guard (the one code unit — TDD it first): `hooks/devlog_guard.py` +
   `tests/test_devlog_guard.py` + the launchers `hooks/run-guard.{cmd,sh}` + `hooks/hooks.json`.
3. Commands: `save-work.md`, `continue-work.md` (generic ports reading the §5.1 contract, with all
   §10 hardening baked into the instructions).
4. `templates/*` (CLAUDE.md.tmpl + marker-section file, devlog-README, phase-README, decisions,
   HANDOFF, session, `guard.json`) — all managed content wrapped in `devflow:*` markers.
5. `init-workflow.md` (two-mode; root resolution + refresh-mode; depends on templates existing).
6. `document-feature.md`, `demo-guide.md`.
7. `skills/devflow-method/SKILL.md`.
8. README + local-install + the full §9 verification pass.

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
- **The guard's own test:** a pytest for `devlog_guard.py` covering: no-ledger; missing
  `Devlog-dir:`; a normal task missing each required file in turn; a tracked-but-uncommitted file
  (must NOT satisfy); a controller task (report+review only); the all-present pass case;
  `enabled:false` config (no-op); an unparseable `guard.json` (falls back to defaults); and
  `stop_hook_active` set (no-op). Plus a smoke test that each launcher finds a Python and exits 0
  when the structure is absent.

## 10. Robustness & edge cases

**Graceful degradation (global principle).** Every command is written to **never leave a half-state**
and to **report rather than fail**. If a step cannot complete (no git remote, unwritable memory dir,
a process that won't start), it records that plainly in its output/HANDOFF and continues with the
rest — it does not abort the whole save/resume.

**`save-work` hardening:**
- **No git / not a repo:** detect and tell the user; still write `HANDOFF.md` so context is captured,
  skip the commit/verify steps, and say so.
- **No remote / offline:** the push step is **conditional** — push only if an `origin` (or the
  dev-workflow `Push policy`) exists and is reachable; otherwise note "not pushed (no remote)".
- **Detached HEAD / mid-rebase/merge:** detect and stop with a clear message rather than committing
  into a detached or conflicted state.
- **Secret safety:** before `git add -A`, respect `.gitignore` and scan would-be-staged files for
  obvious secret signatures (`.env`, key files, high-entropy tokens); if any match, pause and ask
  rather than committing — honoring "never commit secrets or client data".
- **Nothing to do:** a clean tree with current docs → save-work still writes/refreshes `HANDOFF.md`
  and reports "tree clean, no WIP" (idempotent).

**`continue-work` hardening:**
- **Missing/stale HANDOFF:** if absent, or its timestamp is far behind the latest commit, stop and
  ask where to resume — never guess a start point.
- **Process restart failure:** if a listed Run/Restart command fails, report the failure and the
  command, and continue with what it can — don't loop or silently proceed as if it started.
- **Reality vs handoff mismatch:** run the quickest proof (named test / commit exists); on a
  contradiction, stop and surface the specific mismatch before doing the next action.
- **Divergent git history:** if HEAD has rewound below the handoff's noted commit or the branch
  differs, flag it; a HEAD merely *ahead* is fine.

**Plugin-upgrade semantics.** The per-repo stamped files are the project's own committed record and
are **never** silently rewritten by a plugin update; only `init-workflow` refresh-mode touches them,
and only the marker-sections, only when the user runs it. The commands/guard/skill live in the
plugin and upgrade centrally, so every bootstrapped repo benefits from a fix with no per-repo action.
Backward-compat rule: a guard change must keep reading old ledgers; a template change must keep old
markers valid.

**Concurrency / parallel sessions.** `save-work` refuses while an in-flight subagent it dispatched is
still running (its partial work can't be frozen). The guard is read-only except via git queries and
is safe to run concurrently. The HANDOFF is single-writer by nature (one save-work at a time).

**Internationalization of paths.** All paths are treated as relative to the resolved project root;
no absolute or user-name-specific paths are written into any stamped file, so a bootstrapped repo is
portable across machines and users.

## 11. Component data contracts (the grammars the parts rely on)

The pieces are decoupled, so the **text formats they share are the real interface** and must be
specified exactly. All consumers tolerate extra whitespace and are case-insensitive on keywords.

### 11.1 SDD ledger (`.superpowers/sdd/progress.md`) — read by the guard, written by the loop
- **Phase pointer** (required for the guard to act): a line `Devlog-dir: <path>` where `<path>` is
  the committed phase dir, repo-root-relative (e.g. `docs/devlog/phase1`). Absent → guard fails open.
- **Task status**: one line per task matching `^Task\s+(?P<n>\d+)\s*:\s*(?P<status>\w[\w-]*)\b.*$`.
  The guard acts only on `status == "complete"`. A `close-out`/`closeout`/`controller` substring
  anywhere on a complete line marks it exempt (report+review only).
- The guard reads **only** these two shapes; any other ledger prose is ignored.

### 11.2 Managed marker blocks — written by `init-workflow`, re-found on refresh
```
<!-- devflow:begin <section-id> v<N> -->
… generated content …
<!-- devflow:end <section-id> -->
```
`<section-id>` is stable (e.g. `dev-workflow`, `hard-rule`); `v<N>` lets refresh-mode detect an
out-of-date section and offer to upgrade it. Refresh replaces only the bytes between a matching
begin/end pair; content outside any pair is never touched.

### 11.3 `HANDOFF.md` schema — written by save-work, read by continue-work
A fixed set of labelled fields so continue-work parses it unambiguously: `Timestamp`, `Branch`,
`HEAD`, `WIP-commit` (hash or `none`), `Phase`, `Plan`, `Spec`, `Ledger`, `Next-action` (one
concrete executable step), `Task-status`, `Restart` (list of exact commands or `none`),
`Stateful` (e.g. migration revision or `none`), `Open-question` (or `none`), and the footer
`Resume with: /devflow:continue-work`.

### 11.4 Dev-workflow contract block — written by init, read by save/continue
The §5.1 table, rendered inside a `devflow:begin dev-workflow` marker as a simple
`Key: value` list so both humans and the commands read it the same way.

## 12. Dependencies, assumptions & graceful fallback

- **git** — required for the guard's committed check and for save/continue. No git → guard no-ops;
  save-work still writes HANDOFF and says commits were skipped (§10).
- **Python 3** — required only by the guard; located by the launchers; absent → guard no-ops.
- **superpowers plugin** — devflow *orchestrates* it. `devflow-method` and the greenfield flow call
  `superpowers:brainstorming` / `writing-plans` / `subagent-driven-development`. **If superpowers is
  not installed**, devflow must not hard-fail: the skill/commands detect its absence, say so, point
  the user at installing it, and fall back to a minimal inline brainstorm→plan→build outline so work
  can still proceed. devflow never silently assumes superpowers is present.
- **Claude Code harness** — the instruction file is `CLAUDE.md`. If a repo uses a different
  convention file as well, init-workflow writes `CLAUDE.md` (the authoritative one here) and notes
  the other rather than editing it.
- No network and no non-stdlib Python packages are ever required by any component.

## 13. Failure-mode table (detection → response)

| # | Failure | Detection | Response |
|---|---|---|---|
| 1 | No Python on PATH | launcher finds none | guard exits 0 (no-op); session not blocked |
| 2 | Not a git repo | `git rev-parse` fails | guard no-ops; save-work writes HANDOFF, skips commit, says so |
| 3 | No/unreachable remote | `git remote` empty / push fails | save-work notes "not pushed"; never errors |
| 4 | Detached HEAD / mid-merge | `git symbolic-ref` / state files | save-work stops with a clear message before committing |
| 5 | Would-be secret staged | `.env`/key/entropy scan | save-work pauses and asks before `git add` |
| 6 | Missing/stale HANDOFF | absent or timestamp ≪ latest commit | continue-work asks the user; never guesses |
| 7 | Restart command fails | non-zero exit | continue-work reports the failing command; continues with the rest |
| 8 | Reality ≠ handoff | named test/commit check | continue-work stops and surfaces the specific mismatch |
| 9 | Guard bug / exception | caught at top level | exit 0 (fail open); optional one-line debug log |
| 10 | Huge phase / many tasks | n/a | two batched git calls keep it well under the 30 s timeout |
| 11 | superpowers absent | skill lookup | report + fallback outline; no hard-fail |
| 12 | Re-run init-workflow | existing markers | refresh-mode: update managed sections only, create missing |
| 13 | Corrupt/odd `guard.json` | parse/type check | ignore → built-in defaults; never error |

## 14. Append / idempotency semantics for logs

- `docs/devlog/decisions.md` is **append-only**; init seeds "decision 1: adopted devflow" exactly
  once (guarded by a marker), and re-runs never duplicate it.
- `docs/devlog/sessions/<today>.md` is **append** — a re-run or a later save-work on the same day
  adds a dated entry rather than overwriting the file.
- `docs/devlog/HANDOFF.md` is the one **overwrite** file (a living pointer); its prior content is
  not history — the session file carries the narrative.

## 15. Clean removal / uninstall

- `/plugin uninstall devflow` removes the commands/guard/skill globally; a repo's committed
  `docs/devlog/` + CLAUDE.md remain (they are the project's own record) and keep working as plain docs.
- To detach a single repo without uninstalling the plugin: set `guard.json` `enabled:false` (keeps
  the trail, silences the guard) — a documented, reversible off-switch. No marker-section is force-
  removed automatically; the user deletes them if they want, and the markers make that unambiguous.

## 16. Definition of Done (acceptance criteria)

The kit is "done" when, on the target Windows box:
1. The plugin installs from the local marketplace and all five commands + the skill are listed.
2. `devlog_guard.py` passes its full pytest (§9) including every §13 edge case.
3. The guard **blocks** a contrived incomplete-trail repo with the exact file list, then **passes**
   once the trail is committed — and **never** fires in a repo without `docs/devlog/`.
4. `init-workflow` produces a correct scaffold in both a new empty dir and a small existing repo,
   **non-destructively and idempotently** (a second run changes nothing it shouldn't).
5. A save-work → `/clear` → continue-work round-trip resumes with zero loss and a clean tree.
6. devflow-kit **dogfoods itself**: its own repo carries a `docs/devlog/` trail produced by this
   very workflow.

## 17. Resolved decisions (were open questions)

All settled 2026-10-27; no open questions remain.

1. **Names are final.** Plugin `devflow`; commands `/devflow:save-work`, `/devflow:continue-work`,
   `/devflow:init-workflow`, `/devflow:document-feature`, `/devflow:demo-guide`; local marketplace
   `devflow-kit`.
2. **`document-feature` + `demo-guide` ship in the first version** (not deferred).
3. **Memory seeding is best-effort-and-skip.** `CLAUDE.md` + `docs/devlog/` are the guaranteed source
   of truth; a memory seed is an enhancement written only if the harness memory dir is writable, and
   its absence never fails a command or degrades the workflow.
4. **Default commit trailer:** `init-workflow` asks for the attribution line. If the user skips, it
   falls back to the current session's attribution line and records it in the editable
   `dev-workflow` contract block (marked "confirm") — never left blank, never silently wrong.
   The contract block's `Commit trailer` is authoritative thereafter; save-work reads it.
