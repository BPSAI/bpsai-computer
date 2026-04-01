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
