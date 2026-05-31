"""Startup banner (Spring Boot style)."""

from __future__ import annotations

import sys

# Block-letter "NIDARI" (figlet standard)
_BANNER = r"""
 _   _ ___ ____    _    ____  ___ 
| \ | |_ _|  _ \  / \  |  _ \|_ _|
|  \| || || | | |/ _ \ | |_) || | 
| |\  || || |_| / ___ \|  _ < | | 
|_| \_|___|____/_/   \_\_| \_\___|
""".strip("\n")


def print_startup_banner(
    *,
    title: str = "Nidari API",
    version: str = "5.0.0",
    env: str = "development",
    stream=None,
) -> None:
    """Print ASCII banner to console on startup."""
    out = stream or sys.stdout
    print(_BANNER, file=out)
    print(f"  :: {title} ::  (v{version})  [{env}]", file=out)
    print(file=out)
