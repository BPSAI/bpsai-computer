"""Tests for license discovery from license.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from computer.license_discovery import discover_license_id, LicenseDiscoveryError


class TestDiscoverFromHomeDir:
    """Test discovery of license_id from ~/.paircoder/license.json."""

    def test_reads_license_id_from_file(self, tmp_path: Path):
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text(json.dumps({
            "payload": {"license_id": "lic-abc-123"}
        }))
        result = discover_license_id(home_dir=tmp_path)
        assert result == "lic-abc-123"

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(LicenseDiscoveryError, match="No license found"):
            discover_license_id(home_dir=tmp_path)

    def test_error_message_includes_install_hint(self, tmp_path: Path):
        with pytest.raises(LicenseDiscoveryError, match="bpsai-pair license install"):
            discover_license_id(home_dir=tmp_path)

    def test_invalid_json_raises(self, tmp_path: Path):
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text("not json")
        with pytest.raises(LicenseDiscoveryError, match="Failed to read"):
            discover_license_id(home_dir=tmp_path)

    def test_missing_payload_key_raises(self, tmp_path: Path):
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text(json.dumps({"other": "data"}))
        with pytest.raises(LicenseDiscoveryError, match="Missing"):
            discover_license_id(home_dir=tmp_path)

    def test_missing_license_id_in_payload_raises(self, tmp_path: Path):
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text(json.dumps({"payload": {"other": "val"}}))
        with pytest.raises(LicenseDiscoveryError, match="Missing"):
            discover_license_id(home_dir=tmp_path)


class TestEnvVarOverride:
    """Test BPSAI_LICENSE_FILE env var overrides default path."""

    def test_env_var_points_to_custom_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        custom_file = tmp_path / "custom" / "license.json"
        custom_file.parent.mkdir(parents=True)
        custom_file.write_text(json.dumps({
            "payload": {"license_id": "lic-env-override"}
        }))
        monkeypatch.setenv("BPSAI_LICENSE_FILE", str(custom_file))
        result = discover_license_id(home_dir=tmp_path)
        assert result == "lic-env-override"

    def test_env_var_missing_file_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("BPSAI_LICENSE_FILE", str(tmp_path / "nope.json"))
        with pytest.raises(LicenseDiscoveryError, match="No license found"):
            discover_license_id(home_dir=tmp_path)


class TestConfigOverride:
    """Test that config license_id takes priority (tested via daemon integration)."""

    def test_config_license_id_skips_discovery(self, tmp_path: Path):
        """When config has license_id, discovery should not be needed."""
        # This is really a daemon-level test; here we just verify
        # discover_license_id works independently.
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text(json.dumps({
            "payload": {"license_id": "lic-from-file"}
        }))
        # Config override is tested in test_daemon.py
        result = discover_license_id(home_dir=tmp_path)
        assert result == "lic-from-file"
