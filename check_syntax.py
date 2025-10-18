#!/usr/bin/env python3
"""
check_syntax.py — Syntax + pylint checks for Python files (no ruff).

Usage:
  python check_syntax.py [--staged] [--path .] [--workers N]
                         [--no-pylint] [--pylint-errors-only]

Defaults:
  - Syntax check (py_compile) always ON.
  - Pylint is ON by default (strict). Use --pylint-errors-only to report only E/F.
  - If 'pylint' is not on PATH, falls back to 'python -m pylint'.

Exit codes:
  0  All good
  1  Found syntax and/or pylint issues
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


# ---------------- file collection ----------------

def iter_pyfiles(root: Path, staged: bool = False) -> Iterable[Path]:
    """Yield Python files to check, optionally limited to git-staged files."""
    if staged:
        try:
            res = subprocess.run(
                ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
                capture_output=True,
                text=True,
                check=True,        # explicit for pylint W1510
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: --staged used outside a Git repo; falling back to full scan", file=sys.stderr)
        else:
            for line in res.stdout.splitlines():
                p = Path(line)
                excluded = set(p.parts) & EXCLUDES
                if p.suffix == ".py" and p.exists() and not excluded:
                    yield p
            return

    for p in root.rglob("*.py"):
        if set(p.parts) & EXCLUDES:
            continue
        yield p


# ---------------- syntax check ----------------

def compile_one(path: Path) -> Tuple[Path, Exception | None]:
    """Compile one Python file to bytecode to detect syntax errors."""
    try:
        py_compile.compile(str(path), doraise=True)
        return (path, None)
    except (py_compile.PyCompileError, OSError) as exc:
        return (path, exc)


def syntax_check(files: List[Path], workers: int) -> int:
    """Run syntax check (py_compile) for all files concurrently."""
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


# ---------------- pylint helpers ----------------

def _pylint_cmd_base() -> list[str] | None:
    """Return a command prefix to run pylint (binary preferred, fallback to `python -m pylint`)."""
    if shutil.which("pylint"):
        return ["pylint"]
    if importlib.util.find_spec("pylint") is not None:
        return [sys.executable, "-m", "pylint"]
    return None


def run_pylint(files: list[Path], errors_only: bool = False) -> int:
    """Run pylint over files; return pylint exit code (0=clean)."""
    if not files:
        print("No Python files to lint.", file=sys.stderr)
        return 0

    cmd_base = _pylint_cmd_base()
    if not cmd_base:
        print("ℹ pylint not found — skipping (install with `pip install pylint`).")
        return 0

    print("▶ pylint ...")

    # Discover rcfile: prefer .pylintrc, then pyproject.toml if present.
    rcfile = None
    for candidate in (".pylintrc", "pyproject.toml"):
        if Path(candidate).is_file():
            rcfile = candidate
            break

    base_args = [*cmd_base]
    if rcfile:
        base_args += ["--rcfile", rcfile]

    # Pretty output without score; jobs=0 uses all cores.
    base_args += ["--score=n", "--jobs=0"]

    if errors_only:
        # Only report errors/fatal messages (friendlier for pre-commit).
        base_args += ["-E"]  # --errors-only

    rc = 0
    paths = [str(p) for p in files]
    for group in _chunked(paths, CHUNK):
        rc_part = _run_cmd(base_args + group)
        rc = rc or rc_part
    return rc


def _run_cmd(cmd: list[str]) -> int:
    """Run a subprocess command and return its exit code (no exception on failure)."""
    proc = subprocess.run(cmd, check=False)  # explicit for pylint W1510
    return proc.returncode


def _chunked(seq: list[str], size: int) -> Iterable[list[str]]:
    """Yield slices of 'seq' with at most 'size' elements."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ---------------- main ----------------

def main() -> int:
    """Entry point: run syntax check and (by default) pylint."""
    ap = argparse.ArgumentParser(description="Syntax + pylint checks for Python files (no ruff).")
    ap.add_argument("--staged", action="store_true", help="Only check git staged Python files")
    ap.add_argument("--path", default=".", help="Root path to scan (default: .)")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)

    ap.add_argument("--no-pylint", action="store_true", help="Disable pylint (not recommended)")
    ap.add_argument("--pylint-errors-only", action="store_true", help="pylint: only report errors (E/F)")

    args = ap.parse_args()

    root = Path(args.path).resolve()
    files = list(iter_pyfiles(root, staged=args.staged))
    files.sort()

    exit_code = 0
    exit_code = exit_code or syntax_check(files, workers=args.workers)

    if not args.no_pylint:
        exit_code = exit_code or run_pylint(files, errors_only=args.pylint_errors_only)

    if exit_code == 0:
        print("✅ All checks passed.")
    else:
        print("❌ Checks failed.", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
