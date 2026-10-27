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

def test_non_object_json_stdin_exits_zero(tmp_path):
    import os as _os
    _init_repo(tmp_path)
    _phase(tmp_path)
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _commit_all(tmp_path)
    for payload in ("null", "123", '"hi"', "[1,2]", "true"):
        r = subprocess.run([sys.executable, str(GUARD)], input=payload,
                           capture_output=True, text=True,
                           env={"CLAUDE_PROJECT_DIR": str(tmp_path),
                                "PATH": _os.environ["PATH"]})
        assert r.returncode == 0, f"stdin={payload!r} -> rc={r.returncode} stderr={r.stderr}"

def test_review_diff_requires_digit_after_r(tmp_path):
    _init_repo(tmp_path)
    p = _phase(tmp_path)
    for name in ["task-01-brief.md", "task-01-report.md", "task-01-review.md"]:
        (p / name).write_text("x", encoding="utf-8")
    (p / "tests" / "task-01-tests.txt").write_text("x", encoding="utf-8")
    # a .diff that is NOT task-01-r<digit> must not satisfy the diff requirement
    (p / "reviews" / "task-01-rollback-notes.diff").write_text("x", encoding="utf-8")
    _ledger(tmp_path, "Devlog-dir: docs/devlog/phase1\nTask 1: complete\n")
    _commit_all(tmp_path)
    g = _import_guard()
    assert g.evaluate(tmp_path) != []       # still missing a real review diff
    (p / "reviews" / "task-01-r1.diff").write_text("x", encoding="utf-8")
    _commit_all(tmp_path, "add r1")
    g2 = _import_guard()
    assert g2.evaluate(tmp_path) == []
