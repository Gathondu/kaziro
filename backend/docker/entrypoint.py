from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Final

_ENV_JSON_KEY: Final[str] = "KAZIRO_BACKEND_ENV_JSON"


def _hydrate_runtime_environment() -> None:
    """Load JSON env payload from Secrets Manager-injected variable."""
    raw = os.getenv(_ENV_JSON_KEY)
    if not raw:
        return

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{_ENV_JSON_KEY} must be a JSON object")

    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if key in os.environ:
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            # Empty strings are treated as "disabled override":
            # we skip setting the env so backend defaults can apply.
            continue
        if isinstance(value, (str, int, float, bool)):
            os.environ[key] = str(value)


def main() -> int:
    _hydrate_runtime_environment()
    command = sys.argv[1:]
    if not command:
        raise ValueError("Entrypoint requires a command")
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
