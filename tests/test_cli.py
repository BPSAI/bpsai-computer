"""Tests for CLI argument parsing."""

from computer.cli import parse_args


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
