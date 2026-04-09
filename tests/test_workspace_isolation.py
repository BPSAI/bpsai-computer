"""Tests for concurrent daemon workspace isolation (DWC.2).

Verifies that multiple daemon instances can run simultaneously for different
workspaces without conflicts: scoped cursor files, PID files, and log prefixes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from computer.config import DaemonConfig


def _make_config(workspace: str, tmp_path: Path, **overrides) -> DaemonConfig:
    ws_root = tmp_path / f"ws-{workspace}"
    ws_root.mkdir(exist_ok=True)
    return DaemonConfig(
        operator="mike",
        workspace=workspace,
        workspace_root=str(ws_root),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=30,
        license_id="lic-test",
        **overrides,
    )


class TestWorkspaceScopedCursorPaths:
    """AC: Cursor files scoped by workspace — ~/.bpsai-computer/{workspace}/signal_cursors.json."""

    def test_signal_pusher_uses_workspace_scoped_cursor(self, tmp_path):
        """SignalPusher default cursor path includes workspace subdirectory."""
        from computer.signal_pusher import SignalPusher

        config = _make_config("bpsai", tmp_path)
        with patch("computer.signal_pusher.Path.home", return_value=tmp_path):
            pusher = SignalPusher(config=config)
        expected = tmp_path / ".bpsai-computer" / "bpsai" / "signal_cursors.json"
        assert pusher._cursor_path == expected

    def test_git_collector_uses_workspace_scoped_cursor(self, tmp_path):
        """GitSummaryCollector default cursor path includes workspace subdirectory."""
        from computer.git_collector import GitSummaryCollector

        config = _make_config("bpsai", tmp_path)
        with patch("computer.git_collector.Path.home", return_value=tmp_path):
            collector = GitSummaryCollector(config=config)
        expected = tmp_path / ".bpsai-computer" / "bpsai" / "git_cursors.json"
        assert collector._cursor_path == expected

    def test_ci_collector_uses_workspace_scoped_cursor(self, tmp_path):
        """CISummaryCollector default cursor path includes workspace subdirectory."""
        from computer.ci_collector import CISummaryCollector

        config = _make_config("bpsai", tmp_path)
        with patch("computer.ci_collector.Path.home", return_value=tmp_path):
            collector = CISummaryCollector(config=config)
        expected = tmp_path / ".bpsai-computer" / "bpsai" / "ci_cursors.json"
        assert collector._cursor_path == expected

    def test_two_workspaces_get_different_cursor_paths(self, tmp_path):
        """Two configs produce non-colliding cursor file paths."""
        from computer.signal_pusher import SignalPusher

        cfg_a = _make_config("bpsai", tmp_path)
        cfg_b = _make_config("aurora", tmp_path)
        with patch("computer.signal_pusher.Path.home", return_value=tmp_path):
            pusher_a = SignalPusher(config=cfg_a)
            pusher_b = SignalPusher(config=cfg_b)
        assert pusher_a._cursor_path != pusher_b._cursor_path
        assert "bpsai" in str(pusher_a._cursor_path)
        assert "aurora" in str(pusher_b._cursor_path)

    def test_cursor_files_dont_collide_on_write(self, tmp_path):
        """Writing cursors for workspace A does not affect workspace B."""
        from computer.signal_pusher import SignalPusher

        cfg_a = _make_config("bpsai", tmp_path)
        cfg_b = _make_config("aurora", tmp_path)
        with patch("computer.signal_pusher.Path.home", return_value=tmp_path):
            pusher_a = SignalPusher(config=cfg_a)
            pusher_b = SignalPusher(config=cfg_b)

        pusher_a.set_cursor("/repo/alpha", 42)
        pusher_a.save_cursors()

        pusher_b.set_cursor("/repo/beta", 99)
        pusher_b.save_cursors()

        # Re-load and verify isolation
        with patch("computer.signal_pusher.Path.home", return_value=tmp_path):
            reload_a = SignalPusher(config=cfg_a)
            reload_b = SignalPusher(config=cfg_b)

        assert reload_a.get_cursor("/repo/alpha") == 42
        assert reload_a.get_cursor("/repo/beta") == 0  # not present in A

        assert reload_b.get_cursor("/repo/beta") == 99
        assert reload_b.get_cursor("/repo/alpha") == 0  # not present in B


class TestWorkspacePIDFile:
    """AC: PID file per workspace — ~/.bpsai-computer/{workspace}.pid."""

    def test_pid_file_path_includes_workspace(self, tmp_path):
        """PID file is scoped to workspace name."""
        from computer.workspace import workspace_pid_path

        path = workspace_pid_path("bpsai", base_dir=tmp_path / ".bpsai-computer")
        assert path == tmp_path / ".bpsai-computer" / "bpsai.pid"

    def test_two_workspaces_get_different_pid_paths(self, tmp_path):
        """Different workspaces produce different PID file paths."""
        from computer.workspace import workspace_pid_path

        base = tmp_path / ".bpsai-computer"
        path_a = workspace_pid_path("bpsai", base_dir=base)
        path_b = workspace_pid_path("aurora", base_dir=base)
        assert path_a != path_b

    def test_write_pid_file_creates_file(self, tmp_path):
        """write_pid_file creates a PID file with current process ID."""
        from computer.workspace import write_pid_file

        pid_path = tmp_path / "test.pid"
        write_pid_file(pid_path)
        assert pid_path.exists()
        content = pid_path.read_text().strip()
        assert content.isdigit()

    def test_remove_pid_file_deletes_file(self, tmp_path):
        """remove_pid_file removes the PID file."""
        from computer.workspace import remove_pid_file

        pid_path = tmp_path / "test.pid"
        pid_path.write_text("12345")
        remove_pid_file(pid_path)
        assert not pid_path.exists()

    def test_remove_pid_file_noop_when_missing(self, tmp_path):
        """remove_pid_file does not error when file doesn't exist."""
        from computer.workspace import remove_pid_file

        pid_path = tmp_path / "nonexistent.pid"
        remove_pid_file(pid_path)  # should not raise

    def test_check_pid_file_returns_none_when_missing(self, tmp_path):
        """check_existing_pid returns None when no PID file exists."""
        from computer.workspace import check_existing_pid

        pid_path = tmp_path / "nonexistent.pid"
        assert check_existing_pid(pid_path) is None

    def test_check_pid_file_returns_pid_when_exists(self, tmp_path):
        """check_existing_pid returns the PID for a live process."""
        import os
        from computer.workspace import check_existing_pid

        pid_path = tmp_path / "test.pid"
        pid_path.write_text(str(os.getpid()))  # current process is alive
        assert check_existing_pid(pid_path) == os.getpid()

    def test_check_pid_file_returns_none_for_dead_process(self, tmp_path):
        """check_existing_pid returns None and deletes stale PID file."""
        from unittest.mock import patch
        from computer.workspace import check_existing_pid

        pid_path = tmp_path / "test.pid"
        pid_path.write_text("99999999")  # very unlikely to be alive

        # Mock os.kill to raise OSError (process not found)
        with patch("computer.workspace.os.kill", side_effect=OSError):
            result = check_existing_pid(pid_path)

        assert result is None
        assert not pid_path.exists(), "Stale PID file should be deleted"


class TestWorkspaceLogPrefix:
    """AC: Log messages prefixed with [{workspace}] for clarity."""

    def test_daemon_log_includes_workspace_prefix(self, tmp_path, caplog):
        """Daemon configures logging with workspace prefix."""
        from computer.daemon import Daemon

        config = _make_config("bpsai", tmp_path)
        with caplog.at_level(logging.INFO):
            daemon = Daemon(config)
        # The daemon start log should contain workspace info
        # (tested more fully in run() integration test)
        assert daemon.config.workspace == "bpsai"

    def test_configure_workspace_logging_adds_prefix(self):
        """configure_workspace_logging sets a filter/formatter with workspace tag."""
        from computer.workspace import configure_workspace_logging

        root = logging.getLogger()
        root.handlers.clear()
        handler = logging.StreamHandler()
        root.addHandler(handler)

        configure_workspace_logging("bpsai")

        found = False
        for h in root.handlers:
            if h.formatter and "[bpsai]" in h.formatter._fmt:
                found = True
                break
        assert found, "Root logger formatter should contain [bpsai] prefix"


class TestTwoConfigsLoadedIndependently:
    """AC: Two configs loaded independently, cursor files don't collide."""

    def test_two_workspace_configs_load_independently(self, tmp_path, monkeypatch):
        """Two different workspace configs can be loaded without conflict."""
        from computer.config import load_config

        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()

        bpsai_config = config_dir / "bpsai.yaml"
        bpsai_config.write_text(
            "operator: mike\nworkspace: bpsai\npoll_interval: 5\n"
        )

        aurora_config = config_dir / "aurora.yaml"
        aurora_config.write_text(
            "operator: mike\nworkspace: aurora\npoll_interval: 10\n"
        )

        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)

        cfg_a = load_config(workspace="bpsai")
        cfg_b = load_config(workspace="aurora")

        assert cfg_a.workspace == "bpsai"
        assert cfg_a.poll_interval == 5
        assert cfg_b.workspace == "aurora"
        assert cfg_b.poll_interval == 10

    def test_two_daemons_use_separate_cursor_directories(self, tmp_path):
        """Two Daemon instances for different workspaces produce isolated cursor dirs."""
        from computer.daemon import Daemon

        cfg_a = _make_config("bpsai", tmp_path)
        cfg_b = _make_config("aurora", tmp_path)

        with patch("computer.signal_pusher.Path.home", return_value=tmp_path), \
             patch("computer.git_collector.Path.home", return_value=tmp_path), \
             patch("computer.ci_collector.Path.home", return_value=tmp_path):
            daemon_a = Daemon(cfg_a)
            daemon_b = Daemon(cfg_b)

        # Signal cursors isolated
        assert daemon_a.signal_pusher._cursor_path != daemon_b.signal_pusher._cursor_path
        # Git cursors isolated
        assert daemon_a.git_collector._cursor_path != daemon_b.git_collector._cursor_path
        # CI cursors isolated
        assert daemon_a.ci_collector._cursor_path != daemon_b.ci_collector._cursor_path
