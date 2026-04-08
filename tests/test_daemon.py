"""Tests for the daemon lifecycle (start/stop/shutdown)."""

import asyncio
import json
import signal

import pytest

from computer.config import DaemonConfig
from computer.daemon import Daemon, resolve_license_id
from computer.license_discovery import LicenseDiscoveryError


@pytest.fixture
def config(tmp_path):
    return DaemonConfig(
        operator="mike",
        workspace="bpsai",
        workspace_root=str(tmp_path),
        a2a_url="http://localhost:9999",
        poll_interval=1,
        process_timeout=30,
        license_id="lic-test",
    )


class TestDaemon:
    """Test daemon lifecycle."""

    async def test_daemon_creates_with_config(self, config):
        daemon = Daemon(config)
        assert daemon.config.operator == "mike"
        assert daemon.running is False

    async def test_daemon_stops_on_shutdown(self, config):
        daemon = Daemon(config)
        daemon.running = True
        daemon.shutdown()
        assert daemon.running is False

    async def test_daemon_run_exits_on_shutdown(self, config):
        """Daemon run loop exits promptly when shutdown is called."""
        daemon = Daemon(config)

        async def stop_after_brief():
            await asyncio.sleep(0.1)
            daemon.shutdown()

        asyncio.create_task(stop_after_brief())
        # run() should exit cleanly without hanging
        await asyncio.wait_for(daemon.run(), timeout=5.0)
        assert daemon.running is False


class TestResolveLicenseId:
    """Test license_id resolution: config override vs auto-discovery."""

    def test_config_override_skips_discovery(self, tmp_path):
        """When config has license_id, discovery is not attempted."""
        cfg = DaemonConfig(
            operator="mike", workspace="bpsai",
            workspace_root=str(tmp_path), license_id="lic-from-config",
        )
        result = resolve_license_id(cfg)
        assert result == "lic-from-config"

    def test_auto_discover_from_license_file(self, tmp_path):
        """When config has no license_id, discover from license.json."""
        license_file = tmp_path / ".paircoder" / "license.json"
        license_file.parent.mkdir(parents=True)
        license_file.write_text(json.dumps({
            "payload": {"license_id": "lic-discovered"}
        }))
        cfg = DaemonConfig(
            operator="mike", workspace="bpsai",
            workspace_root=str(tmp_path),
        )
        result = resolve_license_id(cfg, home_dir=tmp_path)
        assert result == "lic-discovered"

    def test_missing_license_raises(self, tmp_path):
        """When no config and no file, raises LicenseDiscoveryError."""
        cfg = DaemonConfig(
            operator="mike", workspace="bpsai",
            workspace_root=str(tmp_path),
        )
        with pytest.raises(LicenseDiscoveryError, match="No license found"):
            resolve_license_id(cfg, home_dir=tmp_path)
