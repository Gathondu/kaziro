#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which

REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_command(command: list[str]) -> list[str] | None:
    if not command:
        return None
    executable = command[0]
    args = command[1:]
    if executable == "pnpm":
        # On Windows, `which("pnpm")` often resolves to a shim that is not directly
        # executable by CreateProcess; prefer the .cmd wrapper.
        if which("pnpm.cmd"):
            return ["pnpm.cmd", *args]
        if which("corepack"):
            return ["corepack", "pnpm", *args]
    if which(executable):
        return command
    return None


def _run(command: list[str], cwd: Path | None = None) -> int:
    location = str(cwd or REPO_ROOT)
    print(f"\n> ({location}) {' '.join(command)}")
    resolved = _resolve_command(command)
    if resolved is None:
        print(f"Command not found: {command[0]}")
        return 127
    try:
        completed = subprocess.run(resolved, cwd=cwd or REPO_ROOT, check=False)
    except FileNotFoundError:
        # Last-resort fallback for Windows shell wrappers.
        completed = subprocess.run(["cmd", "/c", *resolved], cwd=cwd or REPO_ROOT, check=False)
    return completed.returncode


def _staged_files() -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _is_root_markdown(path: str) -> bool:
    return "/" not in path and path.endswith(".md")


def main() -> int:
    staged = _staged_files()
    if not staged:
        print("No staged files. Skipping changed-file linters.")
        return 0

    failed = False

    backend_py = sorted(
        path.removeprefix("backend/")
        for path in staged
        if path.startswith("backend/")
        and path.endswith(".py")
        and "/tests/" not in path
        and "/alembic/" not in path
    )
    if backend_py:
        if (
            _run(["uv", "run", "ruff", "check", *backend_py], cwd=REPO_ROOT / "backend")
            != 0
        ):
            failed = True
        if (
            _run(
                ["uv", "run", "ruff", "format", "--check", *backend_py],
                cwd=REPO_ROOT / "backend",
            )
            != 0
        ):
            failed = True
        if _run(["uv", "run", "mypy", *backend_py], cwd=REPO_ROOT / "backend") != 0:
            failed = True

    frontend_prettier = sorted(
        path.removeprefix("frontend/")
        for path in staged
        if path.startswith("frontend/")
        and Path(path).suffix
        in {
            ".css",
            ".html",
            ".js",
            ".json",
            ".jsx",
            ".md",
            ".mjs",
            ".svelte",
            ".ts",
            ".tsx",
            ".yaml",
            ".yml",
        }
    )
    if frontend_prettier:
        if (
            _run(
                ["pnpm", "exec", "prettier", "--check", *frontend_prettier],
                cwd=REPO_ROOT / "frontend",
            )
            != 0
        ):
            failed = True

    frontend_eslint = sorted(
        path.removeprefix("frontend/")
        for path in staged
        if path.startswith("frontend/")
        and Path(path).suffix in {".js", ".mjs", ".cjs", ".ts", ".svelte"}
    )
    if frontend_eslint:
        if (
            _run(
                ["pnpm", "exec", "eslint", *frontend_eslint], cwd=REPO_ROOT / "frontend"
            )
            != 0
        ):
            failed = True

    docs_md = sorted(
        path
        for path in staged
        if path.endswith(".md")
        and (path.startswith("docs/") or _is_root_markdown(path))
    )
    if docs_md:
        if _run(["pnpm", "dlx", "markdownlint-cli2", *docs_md], cwd=REPO_ROOT) != 0:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
