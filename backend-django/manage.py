#!/usr/bin/env python
"""Django administrative entry point for the parallel Kaziro backend."""

from __future__ import annotations

import os
import sys

from django.core.management import execute_from_command_line

from apps.core.logging_config import configure_logging


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    configure_logging()
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
