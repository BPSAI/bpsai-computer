"""Tests for CLI argument parsing and validation."""

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from computer.cli import main, parse_args


class TestParseArgs:
    """Test CLI argument parsing."""

    def test_required_args(self):
        args = parse_args(["daemon", "--operator", "mike", "--workspace", "bpsai"])
        assert args.operator == "mike"
        assert args.workspace == "bpsai"

    def test_optional_args(self):
        args = parse_args([
            "daemon",
            "--operator", "mike",
            "--workspace", "bpsai",
            "--workspace-root", "/tmp/ws",
            "--a2a-url", "http://localhost:8000",
            "--poll-interval", "10",
            "--process-timeout", "600",
        ])
        assert args.workspace_root == "/tmp/ws"
        assert args.a2a_url == "http://localhost:8000"
        assert args.poll_interval == 10
        assert args.process_timeout == 600

    def test_config_file_arg(self):
        args = parse_args([
            "daemon",
            "--operator", "mike",
            "--workspace", "bpsai",
            "--config", "/tmp/config.yaml",
        ])
        assert args.config == "/tmp/config.yaml"

    def test_defaults_are_none(self):
        """CLI args default to None so they don't override config file."""
        args = parse_args(["daemon", "--operator", "mike", "--workspace", "bpsai"])
        assert args.workspace_root is None
        assert args.a2a_url is None
        assert args.poll_interval is None
        assert args.process_timeout is None


class TestCLIValidation:
    """Test CLI-level validation before daemon starts."""

    def test_invalid_workspace_name_exits(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["daemon", "--operator", "mike", "--workspace", "../etc/passwd"])
        assert exc_info.value.code != 0

    def test_missing_operator_exits(self, tmp_path, monkeypatch):
        """CLI exits with clear error when operator missing after config load."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        with pytest.raises(SystemExit) as exc_info:
            main(["daemon", "--workspace", "bpsai"])
        assert exc_info.value.code != 0
