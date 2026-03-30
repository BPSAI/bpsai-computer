"""CLI entry point for bpsai-computer."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from computer.config import load_config
from computer.daemon import Daemon


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bpsai-computer",
        description="Computer₀ dispatch daemon",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    daemon_p = sub.add_parser("daemon", help="Run the dispatch daemon")
    daemon_p.add_argument("--operator", required=True, help="Operator identity")
    daemon_p.add_argument("--workspace", required=True, help="Workspace identity")
    daemon_p.add_argument("--workspace-root", default=None, help="Root directory for repos")
    daemon_p.add_argument("--a2a-url", default=None, help="A2A backend URL")
    daemon_p.add_argument("--poll-interval", type=int, default=None, help="Seconds between polls")
    daemon_p.add_argument("--process-timeout", type=int, default=None, help="Subprocess timeout (s)")
    daemon_p.add_argument("--config", default=None, help="Path to config YAML")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "daemon":
        config_path = Path(args.config) if args.config else None
        overrides = {
            "operator": args.operator,
            "workspace": args.workspace,
            "workspace_root": args.workspace_root,
            "a2a_url": args.a2a_url,
            "poll_interval": args.poll_interval,
            "process_timeout": args.process_timeout,
        }
        cfg = load_config(config_path=config_path, overrides=overrides)
        daemon = Daemon(cfg)

        def _handle_signal(*_):
            daemon.shutdown()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
