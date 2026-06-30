#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import re
from pathlib import Path
from shutil import which

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = REPO_ROOT / "frontend"


def _resolve_command(command: list[str]) -> list[str] | None:
    if not command:
        return None
    executable = command[0]
    args = command[1:]
    if executable == "pnpm":
        # On Windows, pnpm.CMD forwards `%*` unquoted, so paths containing
        # parentheses (Next.js route groups like `(app)`) break in cmd.exe.
        # Run pnpm's JS entrypoint through Node directly to preserve argv.
        pnpm_cmd = which("pnpm.cmd")
        if pnpm_cmd:
            resolved = _resolve_pnpm_cmd(Path(pnpm_cmd), args)
            if resolved is not None:
                return resolved
        if which("corepack"):
            return ["corepack", "pnpm", *args]
    if which(executable):
        return command
    return None


def _resolve_pnpm_cmd(pnpm_cmd: Path, args: list[str]) -> list[str] | None:
    try:
        body = pnpm_cmd.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r'"%~dp0\\node\.exe"\s+"%~dp0\\([^"]+pnpm\.mjs)"', body)
    if match is None:
        return None
    node_exe = pnpm_cmd.parent / "node.exe"
    pnpm_mjs = (pnpm_cmd.parent / match.group(1)).resolve()
    if not node_exe.exists() or not pnpm_mjs.exists():
        return None
    return [str(node_exe), str(pnpm_mjs), *args]


def _node_tool(script: Path, *args: str) -> list[str]:
    node = which("node")
    if node is None:
        return ["node", str(script), *args]
    return [node, str(script), *args]


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
        and "/migrations/" not in path
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
            ".ts",
            ".tsx",
            ".yaml",
            ".yml",
        }
    )
    if frontend_prettier:
        if (
            _run(
                _node_tool(
                    FRONTEND_ROOT / "node_modules" / "prettier" / "bin" / "prettier.cjs",
                    "--check",
                    *frontend_prettier,
                ),
                cwd=FRONTEND_ROOT,
            )
            != 0
        ):
            failed = True

    frontend_eslint = sorted(
        path.removeprefix("frontend/")
        for path in staged
        if path.startswith("frontend/")
        and Path(path).suffix in {".js", ".mjs", ".cjs", ".ts", ".tsx"}
    )
    if frontend_eslint:
        if (
            _run(
                _node_tool(
                    FRONTEND_ROOT / "node_modules" / "eslint" / "bin" / "eslint.js",
                    *frontend_eslint,
                ),
                cwd=FRONTEND_ROOT,
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
