"""Shared CLI entry for API processes."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .infrastructure.config.settings import init_settings


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config-path",
        dest="config_path",
        type=str,
        default=None,
        help="Path to config.yaml (default: <runtime>/res/conf/config.yaml)",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (only when --config-path is not set)",
    )
    return parser


def run_server(
    app: str,
    *,
    default_port: int = 8000,
    description: str = "Nidari API server",
) -> None:
    parser = build_parser(description)
    parser.set_defaults(port=default_port)
    args = parser.parse_args()

    config_path = Path(args.config_path).expanduser().resolve() if args.config_path else None
    init_settings(config_path)

    reload = args.reload and args.config_path is None
    if args.reload and args.config_path:
        print("Warning: --reload is disabled when --config-path is set")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=reload,
    )
