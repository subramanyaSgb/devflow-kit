# devflow

**A portable Claude Code plugin that makes any project resumable, documented, and review-disciplined — and ends context loss between sessions.**

<p>
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg">
  <img alt="Platform: Windows / macOS / Linux" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue">
  <img alt="Runtime: Python 3 stdlib only" src="https://img.shields.io/badge/runtime-Python%203%20(stdlib%20only)-blue">
  <img alt="Dependencies: none" src="https://img.shields.io/badge/dependencies-none-brightgreen">
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-5A3FD6">
</p>

Install one plugin, run one command, and every project you open follows the same disciplined loop:
**zero-loss session handoffs, a committed `docs/devlog/` trail, a Stop-hook guard that enforces it, and
a one-command bootstrap** — without hand-copying files between repos.

---

## The problem devflow solves

Long coding sessions with an AI assistant all hit the same wall: **the context window fills up.** When it
does, the usual answer is automatic compaction — the assistant silently summarizes the conversation so far
and continues from the summary. That summary is where things quietly go wrong:

| What traditional compaction does | What it costs you |
|---|---|
| **Summarizes lossily and silently.** The model rewrites hundreds of turns into a paragraph. | The *exact next step*, the file you were mid-edit in, the migration revision you were on — gone or blurred. |
| **Keeps a bloated transcript until the limit.** You pay for every stale tool call and dead end still in context. | Tokens (and money) burned carrying history the next step doesn't need. |
| **Guesses when details conflict.** A summary can't tell a superseded decision from a live one. | The assistant confidently acts on a stale fact and contradicts the current code. |
| **Leaves nothing on disk.** The summary lives only in that one session. | Close the session, lose the thread. A teammate — or tomorrow-you — starts from zero. |
| **Isn't reviewable or committed.** No artifact, no diff, no test record. | No audit trail of *why* the code is the way it is. |

devflow replaces that fragile, invisible summary with an **explicit, structured, committed handoff** — and
lets you `/clear` the bloated context on purpose instead of waiting for the window to force a lossy compaction
on you.

---

## How devflow fixes it

Instead of letting the window overflow into an automatic summary, you drive the boundary yourself:

```
  … work …  →  /devflow:save-work  →  /clear  →  /devflow:continue-work  →  … work …
                      │                   │                  │
             writes a structured    wipes the bloated   reads the handoff +
             HANDOFF.md + sweeps     context (tokens     the few docs it points
             every doc for stale     reclaimed)          to — nothing stale
             data, commits it
```

- **`/devflow:save-work`** snapshots true state (git, active phase/plan/task, background processes,
  stateful revisions), performs an **exhaustive stale-data sweep** — for every term the session removed,
  renamed, or shipped, it greps *every* living doc and fixes each hit — then writes a fixed-schema
  `HANDOFF.md` resume contract and commits it. Its hard guarantee:

  > After save-work, **no living doc may contain a statement the current code contradicts.**

- **`/clear`** resets the conversation. Because the next step is reconstructed from the handoff, throwing
  away the transcript loses nothing — and reclaims the entire context window.

- **`/devflow:continue-work`** reads `HANDOFF.md`, loads *only* the docs it names (ledger, plan, spec),
  verifies git state actually matches the contract, restarts background processes, and executes the single
  exact next action. If reality and the handoff disagree, it **stops and surfaces the mismatch** instead of
  guessing.

### Compaction vs. devflow, side by side

| | Automatic compaction | devflow handoff |
|---|---|---|
| **Where the state lives** | Ephemeral, in one chat session | `docs/devlog/HANDOFF.md`, committed to git |
| **Form** | Prose summary, lossy | Fixed-schema contract (branch, HEAD, next-action, restart cmds, …) |
| **Next step** | Inferred, often vague | One concrete, executable instruction |
| **Stale facts** | Can persist and mislead | Swept out of every living doc before saving |
| **Verification on resume** | None | Git state + a named test checked against the contract |
| **Token cost** | Pay for the whole bloated transcript | `/clear` reclaims it; resume from a compact contract |
| **Auditability** | None | Committed trail: decisions, reviews, diffs, test runs |
| **Survives the session?** | No | Yes — any session, any teammate, any machine |

**Why tokens are saved:** a handoff is a few hundred tokens of structured state plus a handful of targeted
doc reads. A pre-compaction transcript is tens of thousands of tokens of conversation you no longer need.
Saving, clearing, and resuming trades the second for the first — and does it *before* the window forces a
worse trade on you.

---

## What you get

- 🔁 **Zero-context-loss handoffs** — `save-work` / `continue-work` round-trip with a committed, verifiable
  resume contract.
- 📒 **A committed devlog trail** — `docs/devlog/` holds decisions, per-session narrative, and per-task
  brief / report / review / diff / **test-run** artifacts, committed *with* the work.
- 🛡️ **A Stop-hook guard** — blocks ending a turn until each task marked `complete` has its full committed
  trail. Test results are first-class: no green checkmark without the evidence on disk.
- 🚀 **One-command bootstrap** — `init-workflow` onboards an existing codebase (reads it, asks what the code
  can't tell it, writes a grounded `CLAUDE.md`) or scaffolds a greenfield project.
- 📖 **Code-grounded docs** — `document-feature` and `demo-guide` generate guidebooks and client-facing
  walkthroughs grounded in the actual code.
- 🔌 **Fail-open and silent by default** — on any unbootstrapped repo, missing Python, or non-git directory,
  every piece no-ops. A globally installed guard **never** gets in your way where it isn't wanted.

---

## Install

```
/plugin marketplace add subramanyaSgb/devflow-kit
/plugin install devflow@devflow-kit
```

That's it — works on any machine with Claude Code, no auth needed (public repo). To update later:

```
/plugin marketplace update devflow-kit
```

<details><summary>Install from a local clone instead</summary>

```
/plugin marketplace add /path/to/devflow-kit
/plugin install devflow@devflow-kit
```
</details>

---

## Commands

| Command | What it does |
|---|---|
| `/devflow:init-workflow` | Bootstrap this repo — onboard an existing codebase or start a greenfield project |
| `/devflow:save-work` | Snapshot work, sweep every living doc for stale data, write `HANDOFF.md`, commit — run before `/clear` |
| `/devflow:continue-work` | Resume exactly where the last session stopped, verified against git state |
| `/devflow:document-feature <name>` | Write a code-grounded guidebook for a feature / module / surface |
| `/devflow:demo-guide <name>` | Write a client-facing walkthrough of a feature (docs only, never touches app code) |

---

## How it works — the loop

Once a repo is bootstrapped, `devflow` orchestrates the **superpowers** development loop and wraps a
devlog / handoff / guard layer around it:

```
brainstorm → write plan → subagent-driven implement → review → commit test artifacts
        ↑                                                               │
        └──────────  /devflow:save-work  ⇄  /devflow:continue-work  ────┘
                          (at every session boundary)
```

The bundled **`devflow-method` skill** is the connective tissue: a lightweight router that states the loop
and defers the *how* of each step to the matching superpowers skill. If superpowers isn't installed, devflow
doesn't hard-fail — it falls back to a minimal inline brainstorm → plan → build and tells you what you're
missing.

---

## The Stop-hook guard

The guard (`hooks/devlog_guard.py`) is the one piece of real code, and it is deliberately conservative:

- **Activates only in a bootstrapped repo** — one that has `docs/devlog/` *and* an SDD ledger
  (`.superpowers/sdd/progress.md` carrying a `Devlog-dir:` line). Everywhere else it is a silent no-op.
- **Checks committed, not merely staged** — a task's required artifacts must exist in `HEAD`, matching the
  rule that the trail is *committed with the work*. One batched `git` call covers an entire phase, so a
  40-task phase is as fast as a 1-task phase and stays well inside the 30 s hook timeout.
- **Fails open on every unexpected error** — a bug in the guard can never wedge your session. Set
  `DEVFLOW_GUARD_DEBUG=1` to get a one-line reason in `.devflow/guard.log`; unset, it is completely silent.
- **Pure Python standard library** — no third-party imports, no environment setup, ever. Covered by a full
  `pytest` suite over its edge cases.

Optional per-project config lives in `.devflow/guard.json` (data only — never evaluated or executed). Want a
lighter trail, a different ledger path, or the guard off for one repo? Set it there; `enabled: false` is the
clean, reversible off-switch.

---

## Requirements & platform

- **Claude Code** with plugin support.
- **git** — for the committed-trail check and save/continue. Absent → the guard no-ops and `save-work` still
  writes `HANDOFF.md`, noting commits were skipped.
- **Python 3** — used only by the guard, located automatically. Absent → the guard no-ops.
- **superpowers plugin** *(recommended)* — devflow orchestrates it; absent → graceful inline fallback.

Built and wired for **Windows** out of the box: the Stop hook runs `hooks/run-guard.cmd`, which finds a
Python 3 (`py -3` / `python` / `python3`) and fails open if none is present. A POSIX launcher
`hooks/run-guard.sh` is included; **macOS / Linux** users add a second `Stop` entry in `hooks/hooks.json`
pointing at it.

---

## Uninstall

```
/plugin uninstall devflow
```

Removes the commands, guard, and skill globally. A repo's committed `docs/devlog/` and `CLAUDE.md` stay —
they are that project's own record and keep working as plain docs. To detach a single repo without
uninstalling, set `enabled: false` in its `.devflow/guard.json`.

---

## Design & license

The full design — data contracts, failure-mode table, and acceptance criteria — lives in
[`docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md`](docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md).
devflow **dogfoods itself**: this repo carries a `docs/devlog/` trail produced by this very workflow.

Released under the **MIT License** (see `license` in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json)).
