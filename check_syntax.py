#!/usr/bin/env python3
"""
check_syntax.py — Syntax + CI-aligned flake8 + strict pylint.

CI parity:
- flake8 pass 1: --select=E9,F63,F7,F82 --show-source --statistics
- flake8 pass 2: --max-complexity=10 --max-line-length=127 --statistics
- pylint:       --max-line-length=127

Usage:
  python check_syntax.py [--staged] [--workers N]
                         [--no-flake8] [--no-pylint]
                         [--targets service tests]
"""

from __future__ import annotations

import argparse
import os
import sys
import py_compile
import subprocess
import shutil
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Tuple

EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}

CHUNK = 100  # avoid "argument list too long"


# ---------------- file discovery ----------------

def iter_pyfiles(root: Path, staged: bool = False) -> Iterable[Path]:
    """Yield Python files to check, optionally limited to git-staged files."""
    if staged:
        try:
            res = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: --staged used outside a Git repo; falling back to full scan", file=sys.stderr)
        else:
            for line in res.stdout.splitlines():
                p = Path(line)
                if p.suffix == ".py" and p.exists() and not (set(p.parts) & EXCLUDES):
                    yield p
            return

    for p in root.rglob("*.py"):
        if set(p.parts) & EXCLUDES:
            continue
        yield p


def resolve_lint_targets(
    staged_files: list[Path],
    default_dirs: list[str],
    fallback_files: list[Path],
) -> list[str]:
    """
    Decide what to pass to flake8/pylint:
    - If there are staged .py files -> use those files (paths as strings).
    - Else, if default dirs exist -> use those dirs (e.g., 'service', 'tests').
    - Else -> use all discovered .py files.
    """
    if staged_files:
        return [str(p) for p in staged_files]
    existing = [d for d in default_dirs if Path(d).exists()]
    if existing:
        return existing
    return [str(p) for p in fallback_files]


# ---------------- syntax check ----------------

def compile_one(path: Path) -> Tuple[Path, Exception | None]:
    """Compile one Python file to bytecode to detect syntax errors early."""
    try:
        py_compile.compile(str(path), doraise=True)
        return (path, None)
    except (py_compile.PyCompileError, OSError) as exc:
        return (path, exc)


def syntax_check(files: List[Path], workers: int) -> int:
    """Run syntax check (py_compile) concurrently for all files."""
    if not files:
        print("No Python files found to check.", file=sys.stderr)
        return 0

    errors: List[Tuple[Path, Exception]] = []
    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(compile_one, f) for f in files]
        for fut in as_completed(futs):
            p, err = fut.result()
            if err is None:
                ok += 1
            else:
                errors.append((p, err))

    if errors:
        print(f"\n✖ Syntax errors in {len(errors)} file(s):", file=sys.stderr)
        for p, err in errors:
            msg = getattr(err, "msg", str(err))
            lineno = getattr(err, "lineno", None)
            if lineno:
                print(f"  - {p}:{lineno}: {msg}", file=sys.stderr)
            else:
                print(f"  - {p}: {msg}", file=sys.stderr)
        print(f"\nChecked {len(files)} files: {ok} OK, {len(errors)} with errors.", file=sys.stderr)
        return 1

    print(f"✓ Syntax OK for {ok} Python files.")
    return 0


# ---------------- subprocess helpers ----------------

def _run_cmd(cmd: list[str]) -> int:
    """Run a subprocess command with repo-root PYTHONPATH and return its exit code."""
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", os.getcwd())
    proc = subprocess.run(cmd, check=False, env=env)
    return proc.returncode


def _chunked(seq: list[str], size: int) -> Iterable[list[str]]:
    """Yield chunks of seq with length <= size."""
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ---------------- flake8 (CI-aligned) ----------------

def run_flake8_errors(targets: list[str]) -> int:
    """
    CI pass 1:
      flake8 <targets> --count --select=E9,F63,F7,F82 --show-source --statistics
    """
    if not _which("flake8"):
        print("ℹ flake8 not found — skipping (pip install flake8).")
        return 0
    print("▶ flake8 (errors: E9,F63,F7,F82) ...")
    base = [
        "flake8",
        "--count",
        "--select=E9,F63,F7,F82",
        "--show-source",
        "--statistics",
    ]
    # In case of many files, chunk to avoid long arg list
    rc = 0
    expanded = targets
    for group in _chunked(expanded, CHUNK):
        rc_part = _run_cmd(base + group)
        rc = rc or rc_part
    return rc


def run_flake8_style(targets: list[str]) -> int:
    """
    CI pass 2:
      flake8 <targets> --count --max-complexity=10 --max-line-length=127 --statistics
    """
    if not _which("flake8"):
        print("ℹ flake8 not found — skipping (pip install flake8).")
        return 0
    print("▶ flake8 (complexity/length) ...")
    base = [
        "flake8",
        "--count",
        "--max-complexity=10",
        "--max-line-length=127",
        "--statistics",
    ]
    rc = 0
    expanded = targets
    for group in _chunked(expanded, CHUNK):
        rc_part = _run_cmd(base + group)
        rc = rc or rc_part
    return rc


def _which(cmd: str) -> bool:
    """Return True if an executable is available on PATH."""
    return shutil.which(cmd) is not None


# ---------------- pylint (strict) ----------------

def _pylint_cmd_base() -> list[str] | None:
    """Return a command prefix to run pylint (binary preferred, fallback to `python -m pylint`)."""
    if shutil.which("pylint"):
        return ["pylint"]
    if importlib.util.find_spec("pylint") is not None:
        return [sys.executable, "-m", "pylint"]
    return None


def run_pylint(targets: list[str]) -> int:
    """Run pylint with max-line-length=127 over the given targets."""
    if not targets:
        print("No targets to lint with pylint.", file=sys.stderr)
        return 0

    cmd_base = _pylint_cmd_base()
    if not cmd_base:
        print("ℹ pylint not found — skipping (pip install pylint).")
        return 0

    print("▶ pylint ...")
    # Prefer project config if available
    rcfile = None
    for candidate in (".pylintrc", "pyproject.toml"):
        if Path(candidate).is_file():
            rcfile = candidate
            break

    base_args = [*cmd_base]
    if rcfile:
        base_args += ["--rcfile", rcfile]

    # Align with CI: line length 127; jobs=0 uses all cores; no score in output
    base_args += ["--max-line-length=127", "--jobs=0", "--score=n"]

    rc = 0
    expanded = targets
    for group in _chunked(expanded, CHUNK):
        rc_part = _run_cmd(base_args + group)
        rc = rc or rc_part
    return rc


# ---------------- main ----------------

def main() -> int:
    """Entry point: syntax check + CI-aligned flake8 + strict pylint."""
    ap = argparse.ArgumentParser(description="Syntax + CI-aligned flake8 + strict pylint checks.")
    ap.add_argument("--staged", action="store_true", help="Only check git staged Python files")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument(
        "--targets",
        nargs="*",
        default=["service", "tests"],
        help="Paths for flake8/pylint (default: service tests)",
    )
    ap.add_argument("--no-flake8", action="store_true", help="Skip flake8 passes")
    ap.add_argument("--no-pylint", action="store_true", help="Skip pylint")
    args = ap.parse_args()

    root = Path(".").resolve()
    files = list(iter_pyfiles(root, staged=args.staged))
    files.sort()

    # 1) Syntax on discovered files (staged or all)
    exit_code = syntax_check(files, workers=args.workers)

    # 2) Lint targets: staged files if any, else default dirs (if present), else all files
    lint_targets = resolve_lint_targets(
        staged_files=[p for p in files if args.staged],
        default_dirs=args.targets,
        fallback_files=files,
    )

    # 3) flake8 (two passes) — align with CI config
    if not args.no_flake8:
        exit_code = exit_code or run_flake8_errors(lint_targets)
        exit_code = exit_code or run_flake8_style(lint_targets)

    # 4) pylint (strict) — align with CI config
    if not args.no_pylint:
        exit_code = exit_code or run_pylint(lint_targets)

    if exit_code == 0:
        print("✅ All checks passed.")
    else:
        print("❌ Checks failed.", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
