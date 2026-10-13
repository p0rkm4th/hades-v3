"""Require experiment orchestrators to target an explicitly isolated project."""

from __future__ import annotations

import os
import re

PROJECT_PATTERN = re.compile(r"hades-v3-exp-[a-z0-9](?:[a-z0-9-]{0,39})\Z")


def compose_project(value: str | None = None) -> str:
    project = value if value is not None else os.environ.get("HADES_COMPOSE_PROJECT", "")
    if not PROJECT_PATTERN.fullmatch(project):
        raise SystemExit(
            "HADES_COMPOSE_PROJECT must be a unique name beginning "
            "'hades-v3-exp-' and contain only lowercase letters, digits, and hyphens"
        )
    return project


def compose_command(compose_file: str) -> list[str]:
    return ["docker", "compose", "-p", compose_project(), "-f", compose_file]
