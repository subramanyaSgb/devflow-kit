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
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return set()
        return {ln.strip().replace("\\", "/") for ln in r.stdout.splitlines() if ln.strip()}
    except Exception as e:
        _debug(root, f"git {args[:2]} failed: {e}")
        return set()


def _required_files(n: int, kinds: list[str]) -> list[tuple[str, str]]:
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

    committed = _git_set(root, ["ls-tree", "-r", "--name-only", "HEAD", "--", phase_dir])

    def present_exact(rel: str) -> bool:
        full = f"{phase_dir}/{rel}"
        return full in committed

    def present_glob(prefix: str) -> bool:
        full = f"{phase_dir}/{prefix}"
        for f in committed:
            if f.startswith(full) and f.endswith(".diff"):
                rest = f[len(full):]
                if rest[:1].isdigit():
                    return True
        return False

    missing: list[str] = []
    for n in sorted(completed):
        line = completed[n]
        is_closeout = any(k in line for k in cfg["closeout_keywords"])
        kinds = cfg["required_closeout"] if is_closeout else cfg["required_normal"]
        gaps = []
        for label, kind in _required_files(n, kinds):
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
    if not isinstance(payload, dict):
        payload = {}
    if payload.get("stop_hook_active"):
        sys.exit(0)
    try:
        root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        missing = evaluate(root)
    except Exception as e:
        try:
            _debug(pathlib.Path(os.getcwd()), f"main crashed: {e}")
        except Exception:
            pass
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
