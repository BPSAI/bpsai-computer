"""Tests for daemon configuration loading."""

import textwrap
from pathlib import Path

import pytest

from computer.config import DaemonConfig, load_config


class TestDaemonConfig:
    """Test DaemonConfig dataclass defaults and validation."""

    def test_required_fields(self):
        cfg = DaemonConfig(operator="mike", workspace="bpsai")
        assert cfg.operator == "mike"
        assert cfg.workspace == "bpsai"

    def test_defaults(self):
        cfg = DaemonConfig(operator="mike", workspace="bpsai")
        assert cfg.a2a_url == "https://a2a.paircoder.ai"
        assert cfg.poll_interval == 5
        assert cfg.process_timeout == 1800
        assert cfg.workspace_root is not None

    def test_custom_values(self):
        cfg = DaemonConfig(
            operator="david",
            workspace="danhil",
            workspace_root="/tmp/ws",
            a2a_url="http://localhost:8000",
            poll_interval=10,
            process_timeout=600,
        )
        assert cfg.operator == "david"
        assert cfg.workspace == "danhil"
        assert cfg.workspace_root == "/tmp/ws"
        assert cfg.a2a_url == "http://localhost:8000"
        assert cfg.poll_interval == 10
        assert cfg.process_timeout == 600


class TestLoadConfig:
    """Test loading config from YAML file with CLI overrides."""

    def test_load_from_yaml(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
            workspace_root: /home/mike/workspace
            a2a_url: https://a2a.paircoder.ai
            poll_interval: 10
            process_timeout: 900
        """))
        cfg = load_config(config_path=config_file)
        assert cfg.operator == "mike"
        assert cfg.workspace == "bpsai"
        assert cfg.workspace_root == "/home/mike/workspace"
        assert cfg.poll_interval == 10
        assert cfg.process_timeout == 900

    def test_cli_overrides_file(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
            poll_interval: 10
        """))
        cfg = load_config(
            config_path=config_file,
            overrides={"operator": "david", "poll_interval": 3},
        )
        assert cfg.operator == "david"
        assert cfg.poll_interval == 3
        # Non-overridden value preserved
        assert cfg.workspace == "bpsai"

    def test_cli_only_no_file(self):
        cfg = load_config(
            config_path=Path("/nonexistent/config.yaml"),
            overrides={
                "operator": "mike",
                "workspace": "bpsai",
                "workspace_root": "/tmp",
            },
        )
        assert cfg.operator == "mike"
        assert cfg.workspace == "bpsai"

    def test_missing_required_raises(self):
        with pytest.raises((TypeError, ValueError)):
            load_config(
                config_path=Path("/nonexistent/config.yaml"),
                overrides={"operator": "mike"},  # missing workspace
            )


class TestAuthConfigFields:
    """Test paircoder_api_url and license_id config fields for JWT auth."""

    def test_paircoder_api_url_default(self):
        cfg = DaemonConfig(operator="mike", workspace="bpsai")
        assert cfg.paircoder_api_url == "https://api.paircoder.ai"

    def test_license_id_default_none(self):
        cfg = DaemonConfig(operator="mike", workspace="bpsai")
        assert cfg.license_id is None

    def test_license_id_custom(self):
        cfg = DaemonConfig(operator="mike", workspace="bpsai", license_id="lic-123")
        assert cfg.license_id == "lic-123"

    def test_paircoder_api_url_custom(self):
        cfg = DaemonConfig(
            operator="mike", workspace="bpsai",
            paircoder_api_url="http://localhost:8080",
        )
        assert cfg.paircoder_api_url == "http://localhost:8080"

    def test_load_auth_fields_from_yaml(self, tmp_path: Path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
            license_id: lic-456
            paircoder_api_url: https://custom.api.paircoder.ai
        """))
        cfg = load_config(config_path=config_file)
        assert cfg.license_id == "lic-456"
        assert cfg.paircoder_api_url == "https://custom.api.paircoder.ai"


class TestWorkspaceConfigResolution:
    """Test per-workspace config file resolution."""

    def test_workspace_specific_config_loaded(self, tmp_path: Path, monkeypatch):
        """When workspace provided, load {workspace}.yaml from config dir."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        ws_config = config_dir / "bpsai.yaml"
        ws_config.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
            poll_interval: 15
        """))
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        cfg = load_config(workspace="bpsai")
        assert cfg.operator == "mike"
        assert cfg.workspace == "bpsai"
        assert cfg.poll_interval == 15

    def test_workspace_falls_back_to_default_config(self, tmp_path: Path, monkeypatch):
        """When workspace.yaml missing, fall back to config.yaml."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        default_config = config_dir / "config.yaml"
        default_config.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
            poll_interval: 20
        """))
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        cfg = load_config(workspace="staging")
        assert cfg.operator == "mike"
        assert cfg.poll_interval == 20

    def test_workspace_missing_config_error(self, tmp_path: Path, monkeypatch):
        """When neither workspace.yaml nor config.yaml exist, raise clear error."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        with pytest.raises(FileNotFoundError, match="No config found"):
            load_config(workspace="staging")

    def test_no_workspace_uses_default_config(self, tmp_path: Path, monkeypatch):
        """When no workspace, use config.yaml (existing behavior)."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        default_config = config_dir / "config.yaml"
        default_config.write_text(textwrap.dedent("""\
            operator: mike
            workspace: bpsai
        """))
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        cfg = load_config()
        assert cfg.operator == "mike"
        assert cfg.workspace == "bpsai"

    def test_workspace_config_with_overrides(self, tmp_path: Path, monkeypatch):
        """CLI overrides still win over workspace config file."""
        config_dir = tmp_path / ".bpsai-computer"
        config_dir.mkdir()
        ws_config = config_dir / "prod.yaml"
        ws_config.write_text(textwrap.dedent("""\
            operator: mike
            workspace: prod
            poll_interval: 10
        """))
        monkeypatch.setattr("computer.config._default_config_dir", lambda: config_dir)
        cfg = load_config(workspace="prod", overrides={"poll_interval": 3})
        assert cfg.poll_interval == 3
        assert cfg.operator == "mike"

    def test_explicit_config_path_ignores_workspace(self, tmp_path: Path):
        """When config_path is explicitly given, workspace resolution is skipped."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(textwrap.dedent("""\
            operator: custom
            workspace: custom-ws
        """))
        cfg = load_config(config_path=config_file, workspace="ignored")
        assert cfg.operator == "custom"
        assert cfg.workspace == "custom-ws"
