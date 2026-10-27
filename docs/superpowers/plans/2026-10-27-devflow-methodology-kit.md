# devflow Methodology Kit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `devflow` Claude Code plugin that packages the HMD development methodology (session handoffs, committed devlog trail, a fail-open Stop-hook guard, a CLAUDE.md source-of-truth pattern, and a two-mode onboarding command) so any project can adopt it by installing one plugin and running one command.

**Architecture:** A local plugin repo at `~/Desktop/devflow-kit/`. The only executable code is `hooks/devlog_guard.py` (pure stdlib, TDD'd) plus two thin launcher scripts. Everything else is declarative: a plugin manifest, five markdown slash-commands, one skill, and a set of text templates the `init-workflow` command stamps into a target project. The guard fails open so the globally-installed hook is a silent no-op in any un-bootstrapped repo.

**Tech Stack:** Claude Code plugin format (`.claude-plugin/plugin.json` + `marketplace.json`, `commands/*.md`, `hooks/hooks.json`, `skills/<name>/SKILL.md`), Python 3 standard library (guard + pytest), git, Windows `.cmd` + POSIX `.sh` launchers.

**Spec:** `docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md` (FINAL). Section references (§N) below point into it.

## Global Constraints

- Plugin name `devflow`; local marketplace name `devflow-kit`. Commands: `/devflow:save-work`, `/devflow:continue-work`, `/devflow:init-workflow`, `/devflow:document-feature`, `/devflow:demo-guide`. (§17.1)
- The guard is **pure Python standard library** — no third-party imports, ever. (§3)
- The guard **fails open (exit 0)** on any error, missing env, missing structure, or `stop_hook_active`. It must never wedge a session. (§3)
- The guard makes **exactly one git call total** (`git ls-tree -r --name-only HEAD`, scoped to the phase dir, 10 s timeout); all per-task checks are Python set lookups. (§3.2) *(As-built: the plan's Task 2 code originally included a second, dead `git ls-files` call; it was dropped during Task 2 review — fix `1064f6c`.)*
- A file satisfies the trail only if it is in the **committed HEAD set**, not merely staged. (§3)
- All content `init-workflow` stamps into a project is wrapped in idempotency markers `<!-- devflow:begin <id> v<N> -->` … `<!-- devflow:end <id> -->`; refresh-mode touches only bytes between a matching pair. (§11.2)
- Commands follow the **graceful-degradation** rule: report rather than fail; never leave a half-state. (§10)
- devflow **orchestrates** superpowers; if superpowers is absent, degrade to a minimal inline outline, never hard-fail. (§12)
- Memory seeding is **best-effort-and-skip**; `CLAUDE.md` + `docs/devlog/` are the guaranteed source of truth. (§17.3)
- Commit trailer for this repo's own commits: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Target box is Windows; the `.cmd` launcher is required, the `.sh` is for portability.

---

### Task 1: Plugin skeleton (manifest + marketplace + README stub)

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `README.md`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a loadable plugin named `devflow` installable from the `devflow-kit` marketplace. Later tasks add `commands/`, `hooks/`, `skills/`, `templates/` which this manifest auto-discovers (Claude Code loads those dirs by convention — the manifest does not enumerate them).

- [ ] **Step 1: Write `.claude-plugin/plugin.json`**

```json
{
  "name": "devflow",
  "version": "0.1.0",
  "description": "Portable development methodology: session handoffs, a committed devlog trail, a fail-open Stop-hook guard, and a two-mode project bootstrap.",
  "author": { "name": "Deevia" },
  "license": "MIT",
  "keywords": ["workflow", "devlog", "handoff", "tdd", "documentation", "bootstrap"]
}
```

- [ ] **Step 2: Write `.claude-plugin/marketplace.json`**

```json
{
  "name": "devflow-kit",
  "owner": { "name": "Deevia" },
  "plugins": [
    { "name": "devflow", "source": "." }
  ]
}
```

- [ ] **Step 3: Write `README.md`** (install + command summary)

````markdown
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
````

- [ ] **Step 4: Verify the manifest is valid JSON**

Run: `python -c "import json,pathlib; [json.loads(pathlib.Path(p).read_text()) for p in ['.claude-plugin/plugin.json','.claude-plugin/marketplace.json']]; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "feat(plugin): devflow manifest + marketplace + README

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: The Stop-hook guard (TDD) + launchers + hooks.json

This is the only executable component. Build it test-first. The guard reads the project root from `$CLAUDE_PROJECT_DIR` (fallback: cwd), reads the SDD ledger, and blocks ending a turn when a `complete` task lacks its committed trail.

> **AS-BUILT NOTE (close-out):** the reference code below is the pre-review version. During Task 2 review (fix commit `1064f6c`) three corrections landed in the shipped guard: (1) `main()` also coerces a non-dict JSON stdin payload to `{}` and wraps root-resolution in the broad try, so it truly fails open on any stdin/path error; (2) the dead `git ls-files` "tracked" call was removed — the guard makes a single `git ls-tree -r HEAD` call; (3) `present_glob` requires a digit immediately after `task-NN-r`. The shipped tests total 11. See `hooks/devlog_guard.py` + `tests/test_devlog_guard.py` for the authoritative version.

**Files:**
- Create: `hooks/devlog_guard.py`
- Create: `tests/test_devlog_guard.py`
- Create: `hooks/run-guard.cmd`
- Create: `hooks/run-guard.sh`
- Create: `hooks/hooks.json`

**Interfaces:**
- Consumes: `$CLAUDE_PROJECT_DIR` (project root), stdin JSON `{stop_hook_active?: bool}`, optional `$DEVFLOW_GUARD_DEBUG`, optional `<root>/.devflow/guard.json`.
- Produces: process exit 0 always; on a gap prints `{"decision":"block","reason": "..."}` to stdout. A pure function `evaluate(root: Path) -> list[str]` returning the list of per-task gap messages (empty = clean) that the pytest drives directly.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_devlog_guard.py
import json, subprocess, sys, textwrap
from pathlib import Path
import pytest

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "devlog_guard.py"

def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)

def _init_repo(root: Path):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")

def _commit_all(root: Path, msg="c"):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)

def _ledger(root: Path, body: str):
    d = root / ".superpowers" / "sdd"
    d.mkdir(parents=True, exist_ok=True)
    (d / "progress.md").write_text(textwrap.dedent(body), encoding="utf-8")

def _phase(root: Path):
    p = root / "docs" / "devlog" / "phase1"
    (p / "reviews").mkdir(parents=True, exist_ok=True)
    (p / "tests").mkdir(parents=True, exist_ok=True)
    return p

def _import_guard():
    import importlib.util
    spec = importlib.util.spec_from_file_location("devlog_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_no_ledger_is_clean(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "docs" / "devlog").mkdir(parents=True)
    g = _import_guard()
    assert g.evaluate(tmp_path) == []

def test_missing_devlog_dir_line_fails_open(tmp_path):
    _init_repo(tmp_path)
    _phase(tmp_path)
    _ledger(tmp_path, "Task 1: complete\n")   # no Devlog-dir line
    g = _import_guard()
    assert g.evaluate(tmp_path) == []

def test_normal_task_missing_files_blocks(tmp_path):
    _init_repo(tmp_path)
    _phase(tmp_path)
    _ledger(tmp_path, """
        Devlog-dir: docs/devlog/phase1
        Task 1: complete
    """)
    _commit_all(tmp_path)
    g = _import_guard()
    gaps = g.evaluate(tmp_path)
    assert len(gaps) == 1 and "Task 1" in gaps[0]

def test_all_present_passes(tmp_path):
    _init_repo(tmp_path)
    p = _phase(tmp_path)
    for name in ["task-01-brief.md", "task-01-report.md", "task-01-review.md"]:
        (p / name).write_text("x", encoding="utf-8")
    (p / "reviews" / "task-01-r1.diff").write_text("x", encoding="utf-8")
    (p / "tests" / "task-01-tests.txt").write_text("x", encoding="utf-8")
    _ledger(tmp_path, """
        Devlog-dir: docs/devlog/phase1
        Task 1: complete
    """)
    _commit_all(tmp_path)
    g = _import_guard()
    assert g.evaluate(tmp_path) == []

def test_staged_but_uncommitted_does_not_satisfy(tmp_path):
    _init_repo(tmp_path)
    p = _phase(tmp_path)
    for name in ["task-01-brief.md", "task-01-report.md", "task-01-review.md"]:
        (p / name).write_text("x", encoding="utf-8")
    (p / "reviews" / "task-01-r1.diff").write_text("x", encoding="utf-8")
    (p / "tests" / "task-01-tests.txt").write_text("x", encoding="utf-8")
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _git(tmp_path, "add", "-A")       # staged, NOT committed
    g = _import_guard()
    assert g.evaluate(tmp_path) != []

def test_controller_needs_only_report_and_review(tmp_path):
    _init_repo(tmp_path)
    p = _phase(tmp_path)
    (p / "task-02-report.md").write_text("x", encoding="utf-8")
    (p / "task-02-review.md").write_text("x", encoding="utf-8")
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 2: complete (controller)\n")
    _commit_all(tmp_path)
    g = _import_guard()
    assert g.evaluate(tmp_path) == []

def test_disabled_config_is_noop(tmp_path):
    _init_repo(tmp_path)
    _phase(tmp_path)
    (tmp_path / ".devflow").mkdir()
    (tmp_path / ".devflow" / "guard.json").write_text('{"enabled": false}', encoding="utf-8")
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _commit_all(tmp_path)
    g = _import_guard()
    assert g.evaluate(tmp_path) == []

def test_bad_config_falls_back_to_defaults(tmp_path):
    _init_repo(tmp_path)
    _phase(tmp_path)
    (tmp_path / ".devflow").mkdir()
    (tmp_path / ".devflow" / "guard.json").write_text("{not json", encoding="utf-8")
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _commit_all(tmp_path)
    g = _import_guard()
    assert g.evaluate(tmp_path) != []     # defaults apply -> blocks

def test_stop_hook_active_exits_zero_via_cli(tmp_path):
    _init_repo(tmp_path)
    _phase(tmp_path)
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _commit_all(tmp_path)
    r = subprocess.run([sys.executable, str(GUARD)],
                       input=json.dumps({"stop_hook_active": True}),
                       capture_output=True, text=True,
                       env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ["PATH"]})
    assert r.returncode == 0 and r.stdout.strip() == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/Desktop/devflow-kit && python -m pytest tests/test_devlog_guard.py -q`
Expected: FAIL / errors — `hooks/devlog_guard.py` does not exist yet (collection or import error).

- [ ] **Step 3: Write `hooks/devlog_guard.py`**

```python
#!/usr/bin/env python3
"""Stop-hook guard: block ending a turn until each `complete` SDD task has its
committed devlog trail. Project-agnostic, pure stdlib, fails open on any error.

Reads the project root from $CLAUDE_PROJECT_DIR (fallback: cwd). Spec:
docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md (§3, §11)."""
from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib
import re
import subprocess
import sys

DEFAULTS = {
    "scratch_ledger": ".superpowers/sdd/progress.md",
    "required_normal": ["brief", "report", "review", "diff", "tests"],
    "required_closeout": ["report", "review"],
    "closeout_keywords": ["close-out", "closeout", "controller"],
    "enabled": True,
}

TASK_RE = re.compile(r"^Task\s+(\d+)\s*:\s*(\w[\w-]*)\b(.*)$", re.I | re.M)
DEVLOG_DIR_RE = re.compile(r"^Devlog-dir:\s*(\S+)\s*$", re.I | re.M)


def _debug(root: pathlib.Path, msg: str) -> None:
    if os.environ.get("DEVFLOW_GUARD_DEBUG") != "1":
        return
    try:
        d = root / ".devflow"
        d.mkdir(exist_ok=True)
        with (d / "guard.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{_dt.datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def _load_config(root: pathlib.Path) -> dict:
    cfg = dict(DEFAULTS)
    p = root / ".devflow" / "guard.json"
    try:
        if p.exists():
            raw = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                        cfg[k] = v
    except Exception as e:
        _debug(root, f"config fallback: {e}")
    return cfg


def _git_set(root: pathlib.Path, args: list[str]) -> set[str]:
    try:
        r = subprocess.run(["git", *args], cwd=str(root),
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return set()
        return {ln.strip().replace("\\", "/") for ln in r.stdout.splitlines() if ln.strip()}
    except Exception as e:
        _debug(root, f"git {args[:2]} failed: {e}")
        return set()


def _required_files(n: int, is_closeout: bool, kinds: list[str]) -> list[tuple[str, str]]:
    """Return (label, kind) pairs; kind 'diff' is a glob-prefix, others exact."""
    nn = f"{n:02d}"
    out = []
    for kind in kinds:
        if kind == "report":
            out.append((f"task-{nn}-report.md", "exact"))
        elif kind == "review":
            out.append((f"task-{nn}-review.md", "exact"))
        elif kind == "brief":
            out.append((f"task-{nn}-brief.md", "exact"))
        elif kind == "tests":
            out.append((f"tests/task-{nn}-tests.txt", "exact"))
        elif kind == "diff":
            out.append((f"reviews/task-{nn}-r", "glob"))   # any reviews/task-NN-r*.diff
    return out


def evaluate(root: pathlib.Path) -> list[str]:
    """Pure check: return a list of gap messages (empty = clean/no-op)."""
    cfg = _load_config(root)
    if not cfg["enabled"]:
        return []
    ledger = root / cfg["scratch_ledger"]
    devlog = root / "docs" / "devlog"
    if not ledger.exists() or not devlog.exists():
        return []
    try:
        text = ledger.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        _debug(root, f"ledger read: {e}")
        return []

    m = DEVLOG_DIR_RE.search(text)
    if not m:
        return []
    phase_dir = m.group(1).rstrip("/").replace("\\", "/")

    completed: dict[int, str] = {}
    for tm in TASK_RE.finditer(text):
        n, status, rest = int(tm.group(1)), tm.group(2).lower(), tm.group(3).lower()
        if status == "complete":
            completed.setdefault(n, "")
            completed[n] += " " + rest
    if not completed:
        return []

    tracked = _git_set(root, ["ls-files", "--", phase_dir])
    committed = _git_set(root, ["ls-tree", "-r", "--name-only", "HEAD", "--", phase_dir])

    def present_exact(rel: str) -> bool:
        full = f"{phase_dir}/{rel}"
        return full in committed

    def present_glob(prefix: str) -> bool:
        full = f"{phase_dir}/{prefix}"
        return any(f.startswith(full) and f.endswith(".diff") for f in committed)

    missing: list[str] = []
    for n in sorted(completed):
        line = completed[n]
        is_closeout = any(k in line for k in cfg["closeout_keywords"])
        kinds = cfg["required_closeout"] if is_closeout else cfg["required_normal"]
        gaps = []
        for label, kind in _required_files(n, is_closeout, kinds):
            ok = present_glob(label) if kind == "glob" else present_exact(label)
            if not ok:
                gaps.append(label + ("*.diff" if kind == "glob" else ""))
        if gaps:
            missing.append(f"Task {n}: no committed {', '.join(gaps)} in {phase_dir}/")
    return missing


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if payload.get("stop_hook_active"):
        sys.exit(0)
    root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    try:
        missing = evaluate(root)
    except Exception as e:
        _debug(root, f"evaluate crashed: {e}")
        sys.exit(0)
    if missing:
        reason = (
            "devflow devlog rule: these tasks are marked complete but their committed devlog "
            "trail is incomplete. Commit the full trail into the phase dir "
            "(task-NN-brief.md, task-NN-report.md, task-NN-review.md, reviews/task-NN-rN.diff, "
            "tests/task-NN-tests.txt; close-out/controller tasks need only report+review):\n  - "
            + "\n  - ".join(missing)
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/Desktop/devflow-kit && python -m pytest tests/test_devlog_guard.py -q`
Expected: PASS (all tests green).

- [ ] **Step 5: Write the launchers**

`hooks/run-guard.cmd`:
```bat
@echo off
REM Locate a Python 3 and run the guard; fail open if none is found.
py -3 "%~dp0devlog_guard.py" 2>nul && exit /b 0
python "%~dp0devlog_guard.py" 2>nul && exit /b 0
python3 "%~dp0devlog_guard.py" 2>nul && exit /b 0
exit /b 0
```

`hooks/run-guard.sh`:
```sh
#!/bin/sh
# Locate a Python 3 and run the guard; fail open if none is found.
DIR="$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then exec python3 "$DIR/devlog_guard.py"; fi
if command -v python  >/dev/null 2>&1; then exec python  "$DIR/devlog_guard.py"; fi
exit 0
```

- [ ] **Step 6: Write `hooks/hooks.json`**

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-guard.cmd\"",
            "timeout": 30,
            "statusMessage": "Checking devlog trail is committed"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 7: Make the POSIX launcher executable + verify fail-open when run bare**

Run: `cd ~/Desktop/devflow-kit && chmod +x hooks/run-guard.sh && echo '{}' | CLAUDE_PROJECT_DIR="$(mktemp -d)" python hooks/devlog_guard.py; echo "exit=$?"`
Expected: no output, `exit=0` (empty temp dir has no devlog → no-op).

- [ ] **Step 8: Commit**

```bash
git add hooks/devlog_guard.py hooks/run-guard.cmd hooks/run-guard.sh hooks/hooks.json tests/test_devlog_guard.py
git commit -m "feat(guard): project-agnostic fail-open devlog Stop-hook + launchers + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Templates the bootstrap stamps into a project

All managed content carries `devflow:begin/end` markers (§11.2). These are static files copied/rendered by `init-workflow`; `<today>` and project-specific values are filled by the command at stamp time.

**Files:**
- Create: `templates/CLAUDE.md.tmpl`
- Create: `templates/claude-devworkflow-section.md`
- Create: `templates/devlog-README.md`
- Create: `templates/phase-README.md`
- Create: `templates/decisions.md`
- Create: `templates/HANDOFF.seed.md`
- Create: `templates/session.tmpl.md`
- Create: `templates/guard.json`

**Interfaces:**
- Consumes: nothing executable.
- Produces: the exact text `init-workflow` (Task 5) stamps. The dev-workflow section's `Key: value` grammar (§11.4) is consumed by save-work (Task 4a) and continue-work (Task 4b). The `HANDOFF` field labels (§11.3) are consumed by continue-work.

- [ ] **Step 1: Write `templates/claude-devworkflow-section.md`** (the machine-read contract, §5.1/§11.4)

```markdown
<!-- devflow:begin dev-workflow v1 -->
## Dev workflow (devflow)

This project uses the **devflow** plugin. Session boundaries: `/devflow:save-work` before `/clear`,
`/devflow:continue-work` to resume. A Stop-hook guard enforces the committed devlog trail.

**Contract (read by save-work / continue-work — keep these current):**

- Commit trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`  <!-- confirm -->
- Run commands: none
- Restart commands: none
- Test command: <fill in, e.g. `pytest -q`>
- Stateful resources: none
- Push policy: none
- Scratch ledger: `.superpowers/sdd/progress.md`
<!-- devflow:end dev-workflow -->
```

- [ ] **Step 2: Write `templates/CLAUDE.md.tmpl`** (full HMD-pattern skeleton, §5)

````markdown
# CLAUDE.md — <PROJECT NAME>

<!-- devflow:begin goal v1 -->
> **Goal:** <one sharp sentence>. Full design: `docs/superpowers/specs/<spec>.md` (the source of truth).
<!-- devflow:end goal -->

<!-- devflow:begin hard-rule v1 -->
## HARD RULE: full development documentation

Everything is documented in `docs/devlog/` and committed together with the work.
- Plans, task briefs, implementer reports (with real failing→passing test output), review verdicts,
  per-task test results (`docs/devlog/<phase>/tests/task-NN-tests.txt`), decisions, and session
  summaries all live there. See `docs/devlog/README.md`.
- **Never delete or overwrite** specs/plans/devlog files. Mark superseded ones "SUPERSEDED by …".
- A task is not done until its devlog entries exist (brief, report, review, review diff,
  `tests/task-NN-tests.txt`, ledger row). The Stop-hook guard enforces this.
<!-- devflow:end hard-rule -->

<!-- devflow:begin working-rules v1 -->
## Working rules

- Verify against reality before assuming.
- **Ask when in doubt** — surface unclear decisions to the user.
- Process: superpowers skills (brainstorming → writing-plans → implementation) with a devlog trail.
- **Never commit secrets or client data.**
<!-- devflow:end working-rules -->

## Decisions (agreed with the user)

| # | Topic | Decision |
|---|---|---|
| 1 | Workflow | Adopted devflow (devlog trail + handoffs + guard) |

## Architecture

<filled from the codebase (onboard) or grows as built (greenfield)>

## Running

<how to start / test the project>

<!-- devflow:begin dev-workflow v1 -->
## Dev workflow (devflow)
<!-- (stamped from claude-devworkflow-section.md) -->
<!-- devflow:end dev-workflow -->

## Open questions (confirm during build)

- <none yet>
````

- [ ] **Step 3: Write `templates/devlog-README.md`**

````markdown
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
````

- [ ] **Step 4: Write `templates/phase-README.md`** (per-task close-out checklist)

```markdown
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
```

- [ ] **Step 5: Write `templates/decisions.md`**

```markdown
# Decisions

<!-- devflow:begin decision-1 v1 -->
## 1. Adopted devflow workflow — <DATE>

Adopted the devflow methodology: a committed `docs/devlog/` trail, `/devflow:save-work`
handoffs, and the Stop-hook guard. Rationale: zero-context-loss sessions and an auditable,
test-evidenced development record.
<!-- devflow:end decision-1 -->
```

- [ ] **Step 6: Write `templates/HANDOFF.seed.md`** (schema §11.3)

```markdown
# HANDOFF — resume contract

_Overwritten by `/devflow:save-work`. Not yet populated._

- Timestamp: —
- Branch: —
- HEAD: —
- WIP-commit: none
- Phase: —
- Plan: —
- Spec: —
- Ledger: —
- Next-action: run `/devflow:init-workflow` or start work via `superpowers:brainstorming`
- Task-status: —
- Restart: none
- Stateful: none
- Open-question: none

Resume with: `/devflow:continue-work`
```

- [ ] **Step 7: Write `templates/session.tmpl.md`**

```markdown
# Session <DATE>

- Onboarded/initialized devflow.
- <what happened>
```

- [ ] **Step 8: Write `templates/guard.json`** (optional config, defaults inline, §3.1)

```json
{
  "scratch_ledger": ".superpowers/sdd/progress.md",
  "required_normal": ["brief", "report", "review", "diff", "tests"],
  "required_closeout": ["report", "review"],
  "closeout_keywords": ["close-out", "closeout", "controller"],
  "enabled": true
}
```

- [ ] **Step 9: Commit**

```bash
git add templates/
git commit -m "feat(templates): CLAUDE.md pattern, devlog scaffold, dev-workflow contract, guard config

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4a: `/devflow:save-work` command

**Files:**
- Create: `commands/save-work.md`

**Interfaces:**
- Consumes: the project's `CLAUDE.md` dev-workflow contract block (§11.4) for commit trailer / push policy / stateful resources; the scratch ledger.
- Produces: a committed snapshot, every living doc swept of stale data, `docs/devlog/HANDOFF.md` written to the §11.3 schema, a clean tree.

- [ ] **Step 1: Write `commands/save-work.md`**

````markdown
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
````

- [ ] **Step 2: Verify front-matter + guidance are present**

Run: `grep -c 'devflow:continue-work' commands/save-work.md`
Expected: `2` (step 5 footer + step 7 line).

- [ ] **Step 3: Commit**

```bash
git add commands/save-work.md
git commit -m "feat(command): /devflow:save-work with exhaustive stale-data sweep + HANDOFF schema

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4b: `/devflow:continue-work` command

**Files:**
- Create: `commands/continue-work.md`

**Interfaces:**
- Consumes: `docs/devlog/HANDOFF.md` (§11.3 schema); the CLAUDE.md dev-workflow contract for restart commands + stateful resources.
- Produces: a restored environment and work resumed from the exact next action.

- [ ] **Step 1: Write `commands/continue-work.md`**

````markdown
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
````

- [ ] **Step 2: Verify the HANDOFF reference is present**

Run: `grep -c 'docs/devlog/HANDOFF.md' commands/continue-work.md`
Expected: `1`.

- [ ] **Step 3: Commit**

```bash
git add commands/continue-work.md
git commit -m "feat(command): /devflow:continue-work resume-from-HANDOFF with restart-failure handling

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `/devflow:init-workflow` command (two-mode onboarding)

**Files:**
- Create: `commands/init-workflow.md`

**Interfaces:**
- Consumes: the `templates/*` files (Task 3) — reads them from `${CLAUDE_PLUGIN_ROOT}/templates/`.
- Produces: a bootstrapped project (CLAUDE.md + `docs/devlog/` scaffold + seeds + optional memory + `.devflow/guard.json` ignored), non-destructive and idempotent; routes greenfield into `superpowers:brainstorming`.

- [ ] **Step 1: Write `commands/init-workflow.md`**

````markdown
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
   - Add `.devflow/` to `.gitignore` (guard debug log + local config live there; `guard.json` may be
     committed if the user wants project-wide config).
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
````

- [ ] **Step 2: Verify both modes + fallback are present**

Run: `grep -ciE 'greenfield|onboard|brainstorming|not installed' commands/init-workflow.md`
Expected: `>= 4`.

- [ ] **Step 3: Commit**

```bash
git add commands/init-workflow.md
git commit -m "feat(command): /devflow:init-workflow two-mode onboarding (root resolution, refresh, fallback)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Documentation commands (`document-feature`, `demo-guide`)

**Files:**
- Create: `commands/document-feature.md`
- Create: `commands/demo-guide.md`

**Interfaces:**
- Consumes: the project's code + CLAUDE.md.
- Produces: `docs/guidebook/<name>.md` / `docs/demo-guide/<name>.md`. Documentation only; never changes app code.

- [ ] **Step 1: Write `commands/document-feature.md`**

````markdown
---
description: Write a code-grounded guidebook for ONE feature/module. Docs only; never changes code.
---

Produce (or update) `docs/guidebook/<name>.md` for the feature named in the argument.

1. **Discuss, grounded in code.** Trace the feature end-to-end (entry point → logic → data → UI/output),
   reading the real files. Note exact paths. List anything that looks wrong or stale.
2. **Fix issues with permission.** If you find a real defect, describe it and ask before changing code.
   This command's deliverable is the doc, not code changes.
3. **Write the guide** → `docs/guidebook/<name>.md`: what the feature is, how it works (with
   `path:line` references), inputs/outputs, configuration, edge cases, and how to verify it.
Keep it accurate to the current code — no aspirational claims.
````

- [ ] **Step 2: Write `commands/demo-guide.md`**

````markdown
---
description: Write a client-facing walkthrough of ONE feature. Docs only; never changes code.
---

Produce (or update) `docs/demo-guide/<name>.md` for the feature named in the argument — written for a
client/stakeholder audience, not engineers.

1. Trace the feature in the real code so every claim is true (no invented behavior).
2. Write a **speaking-script walkthrough**: what to show, in what order, what to say, what the
   audience sees, and the value each step demonstrates.
3. Note any caveat an operator should know (approximations, data freshness, access needed).
Documentation only — never change app code.
````

- [ ] **Step 3: Verify output paths**

Run: `grep -l 'docs/guidebook' commands/document-feature.md && grep -l 'docs/demo-guide' commands/demo-guide.md`
Expected: both filenames printed.

- [ ] **Step 4: Commit**

```bash
git add commands/document-feature.md commands/demo-guide.md
git commit -m "feat(command): /devflow:document-feature + /devflow:demo-guide (generalized docs)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `devflow-method` skill (connective tissue)

**Files:**
- Create: `skills/devflow-method/SKILL.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a skill that routes substantive work in a devflow project into the loop + the right superpowers skills; defers to superpowers for the "how"; must not fight superpowers' skill-priority rules (§6).

- [ ] **Step 1: Write `skills/devflow-method/SKILL.md`**

````markdown
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
````

- [ ] **Step 2: Verify front-matter name/description**

Run: `grep -E '^name: devflow-method' skills/devflow-method/SKILL.md && grep -c 'superpowers:' skills/devflow-method/SKILL.md`
Expected: the name line prints and the count is `>= 4`.

- [ ] **Step 3: Commit**

```bash
git add skills/devflow-method/SKILL.md
git commit -m "feat(skill): devflow-method router skill

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Install, verify end-to-end, and dogfood (close-out)

**Files:**
- Create: `docs/devlog/install-notes.md` (the verification record)
- Modify: `README.md` (add a "Verified" line if all checks pass)

**Interfaces:**
- Consumes: the whole plugin.
- Produces: evidence that the §9 verification + §16 Definition-of-Done pass; a dogfooded `docs/devlog/` trail in this repo.

- [ ] **Step 1: Run the guard pytest once more (sole run)**

Run: `cd ~/Desktop/devflow-kit && python -m pytest tests/test_devlog_guard.py -q`
Expected: all PASS. Capture the output into `docs/devlog/install-notes.md`.

- [ ] **Step 2: Guard fail-open smoke test in a throwaway repo**

Run:
```bash
T="$(mktemp -d)"; git -C "$T" init -q
echo '{}' | CLAUDE_PROJECT_DIR="$T" python ~/Desktop/devflow-kit/hooks/devlog_guard.py; echo "exit=$?"
```
Expected: no output, `exit=0` (no devlog → no-op). Record it.

- [ ] **Step 3: Install the plugin locally in Claude Code**

In Claude Code: `/plugin marketplace add ~/Desktop/devflow-kit` then `/plugin install devflow@devflow-kit`. Confirm the five `/devflow:*` commands and the `devflow-method` skill are listed. Record the result.

- [ ] **Step 4: Manual block-then-pass check**

In a throwaway repo, create `.superpowers/sdd/progress.md` with `Devlog-dir: docs/devlog/phase1` + `Task 1: complete`, create empty `docs/devlog/phase1/`, commit, then attempt to end a turn → confirm the Stop hook blocks with the exact file list. Add the five trail files, commit, retry → confirm it passes. Record both outcomes.

- [ ] **Step 5: Write `docs/devlog/install-notes.md`** with the captured evidence (pytest output, smoke-test exit code, install listing, block-then-pass transcript) and the §16 DoD checklist marked.

- [ ] **Step 6: Dogfood — scaffold this repo's own devlog**

Create `docs/devlog/README.md` (from the template), `docs/devlog/decisions.md` (decision 1), and `docs/devlog/sessions/2026-10-27.md` summarizing the build, so devflow-kit itself carries a devflow trail (§16.6).

- [ ] **Step 7: Commit**

```bash
git add docs/devlog README.md
git commit -m "test(verify): §9 verification + §16 DoD evidence; dogfood devflow-kit's own devlog

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- §2.1 layout → Tasks 1–7 (every file created). §2.2 manifest → Task 1. §2.3 save-work sweep → Task 4a.
- §3 guard + §3.1 config + §3.2 impl (batched git, debug, data-only) → Task 2. §4 init two-mode → Task 5.
- §5 CLAUDE.md pattern + §5.1/§11.4 contract → Task 3. §6 skill → Task 7. §7 doc commands → Task 6.
- §8 build order → task ordering. §9 verification + §16 DoD → Task 8. §10 degradation → baked into 4a/4b/5.
- §11 contracts (ledger/markers/HANDOFF/dev-workflow) → Tasks 2 (ledger regex), 3 (markers + HANDOFF seed + contract), 4a (HANDOFF write), 4b (HANDOFF read). §12 dependencies/fallback → Tasks 5 + 7. §13 FMEA → Task 2 tests + 4a/4b/5 instructions. §14 append/idempotency → Tasks 3 + 5. §15 uninstall → README/guard.json `enabled:false` (Tasks 1/3). §17 decisions → applied throughout.
- No gap found.

**2. Placeholder scan** — no "TBD/TODO/handle edge cases/write tests for the above". The guard code and all tests are complete; template bodies are literal; command bodies are complete instructions. The `<...>` angle markers inside *template* files are intentional fill-points stamped by `init-workflow` at runtime, not plan placeholders.

**3. Type consistency** — the guard's public surface `evaluate(root: pathlib.Path) -> list[str]` and `main()` are used identically in the tests (Task 2) and referenced nowhere else. Config keys (`scratch_ledger`, `required_normal`, `required_closeout`, `closeout_keywords`, `enabled`) match across `DEFAULTS`, `templates/guard.json`, and the spec §3.1. The ledger grammar (`Devlog-dir:`, `Task N: complete`) matches across the guard regex (Task 2), templates (Task 3), and spec §11.1. The HANDOFF field labels match across the seed (Task 3), save-work writer (Task 4a), and continue-work reader (Task 4b). The `devflow:begin/end <id> v<N>` marker form matches across templates (Task 3), init-workflow (Task 5), and spec §11.2.

No issues found.
