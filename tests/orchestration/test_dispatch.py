"""Tests for the dispatch engine.

Covers: repo detection, enforcement selection, env scrubbing,
command building, RC/subprocess dispatch, DispatchConfig, dispatch_navigator,
and refusal of unrestricted mode.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computer.orchestration import (
    CREDENTIAL_KEYS,
    DEFAULT_ALLOWED_TOOLS,
    DispatchConfig,
    DispatchError,
    DispatchMode,
    DispatchResult,
    DispatchStatus,
    Dispatcher,
    EnforcementMode,
    RepoClassifier,
    RepoType,
    build_command,
    detect_repo_type,
    scrub_environment,
    select_enforcement,
)


# ---------- detect_repo_type ----------


class TestDetectRepoType:
    def test_paircoder_repo_detected(self, tmp_path):
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()
        assert detect_repo_type(tmp_path) == RepoType.PAIRCODER

    def test_standard_repo_without_paircoder(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert detect_repo_type(tmp_path) == RepoType.STANDARD

    def test_nonexistent_path_raises(self):
        with pytest.raises(DispatchError, match="does not exist"):
            detect_repo_type(Path("/nonexistent/repo/path"))

    def test_file_not_directory_raises(self, tmp_path):
        f = tmp_path / "not_a_dir.txt"
        f.touch()
        with pytest.raises(DispatchError, match="not a directory"):
            detect_repo_type(f)

    def test_paircoder_dir_without_config_is_standard(self, tmp_path):
        """Empty .paircoder dir without config.yaml = not a real PairCoder repo."""
        (tmp_path / ".paircoder").mkdir()
        assert detect_repo_type(tmp_path) == RepoType.STANDARD


# ---------- select_enforcement ----------


class TestSelectEnforcement:
    def test_paircoder_gets_contained_auto(self):
        assert select_enforcement(RepoType.PAIRCODER) == EnforcementMode.CONTAINED_AUTO

    def test_standard_gets_allowed_tools(self):
        assert select_enforcement(RepoType.STANDARD) == EnforcementMode.ALLOWED_TOOLS


# ---------- scrub_environment ----------


class TestScrubEnvironment:
    def test_removes_credential_keys(self):
        env = {
            "PATH": "/usr/bin",
            "HOME": "/home/test",
            "AWS_SECRET_ACCESS_KEY": "secret123",
            "ANTHROPIC_API_KEY": "sk-ant-xxx",
            "GITHUB_TOKEN": "ghp_xxx",
            "DATABASE_URL": "postgres://user:pass@host/db",
        }
        scrubbed = scrub_environment(env)
        assert "PATH" in scrubbed
        assert "HOME" in scrubbed
        assert "AWS_SECRET_ACCESS_KEY" not in scrubbed
        assert "ANTHROPIC_API_KEY" not in scrubbed
        assert "GITHUB_TOKEN" not in scrubbed
        assert "DATABASE_URL" not in scrubbed

    def test_removes_pattern_matched_keys(self):
        env = {
            "PATH": "/usr/bin",
            "MY_SECRET_THING": "hidden",
            "MY_TOKEN_VALUE": "hidden",
            "MY_PASSWORD_FIELD": "hidden",
            "SAFE_VARIABLE": "visible",
        }
        scrubbed = scrub_environment(env)
        assert "MY_SECRET_THING" not in scrubbed
        assert "MY_TOKEN_VALUE" not in scrubbed
        assert "MY_PASSWORD_FIELD" not in scrubbed
        assert "SAFE_VARIABLE" in scrubbed

    def test_preserves_safe_keys(self):
        env = {"PATH": "/usr/bin", "HOME": "/home/user", "LANG": "en_US.UTF-8"}
        scrubbed = scrub_environment(env)
        assert scrubbed == env

    def test_returns_new_dict(self):
        env = {"PATH": "/usr/bin"}
        scrubbed = scrub_environment(env)
        assert scrubbed is not env


# ---------- build_command ----------


class TestBuildCommand:
    def test_contained_auto_command(self, tmp_path):
        cmd = build_command(
            repo_path=tmp_path,
            prompt="Do something",
            enforcement=EnforcementMode.CONTAINED_AUTO,
        )
        assert "claude" in cmd[0]
        assert "-p" in cmd
        assert "--dangerously-skip-permissions" not in cmd
        # Contained-auto uses permission prompt with auto-accept
        assert "Do something" in cmd

    def test_allowed_tools_command(self, tmp_path):
        cmd = build_command(
            repo_path=tmp_path,
            prompt="Do something",
            enforcement=EnforcementMode.ALLOWED_TOOLS,
        )
        assert "claude" in cmd[0]
        assert "-p" in cmd
        assert "--allowedTools" in cmd
        # Should have specific tool list
        idx = cmd.index("--allowedTools")
        tools_str = cmd[idx + 1]
        for tool in DEFAULT_ALLOWED_TOOLS:
            assert tool in tools_str

    def test_no_dangerously_skip_in_any_mode(self, tmp_path):
        """Enforcement is non-negotiable — no unrestricted mode."""
        for mode in EnforcementMode:
            cmd = build_command(tmp_path, "test", mode)
            assert "--dangerously-skip-permissions" not in cmd

    def test_prompt_included(self, tmp_path):
        cmd = build_command(tmp_path, "Run tests now", EnforcementMode.CONTAINED_AUTO)
        assert "Run tests now" in cmd


# ---------- Dispatcher ----------


class TestDispatcher:
    def test_refuses_dispatch_without_enforcement(self, tmp_path):
        """Dispatcher must never allow unrestricted dispatch."""
        (tmp_path / ".git").mkdir()
        d = Dispatcher()
        # Passing a non-EnforcementMode value should raise
        with pytest.raises(DispatchError, match="enforcement"):
            d.dispatch(
                repo_path=tmp_path,
                prompt="do stuff",
                enforcement="none",  # type: ignore[arg-type]
            )

    def test_none_enforcement_auto_detects(self, tmp_path):
        """None enforcement triggers auto-detection, not bypass."""
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()
        d = Dispatcher()
        # None means auto-detect, should pick CONTAINED_AUTO
        with patch("engine.dispatch.dispatcher.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"], returncode=0, stdout="OK", stderr=""
            )
            result = d.dispatch(repo_path=tmp_path, prompt="test", enforcement=None)
            assert result.enforcement == EnforcementMode.CONTAINED_AUTO

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_subprocess_dispatch_success(self, mock_run, tmp_path):
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="Task completed", stderr=""
        )

        d = Dispatcher()
        result = d.dispatch(repo_path=tmp_path, prompt="Run tests")

        assert isinstance(result, DispatchResult)
        assert result.success is True
        assert result.output == "Task completed"
        assert result.enforcement == EnforcementMode.CONTAINED_AUTO
        assert result.method == "subprocess"

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_subprocess_dispatch_failure(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=1, stdout="", stderr="Error occurred"
        )

        d = Dispatcher()
        result = d.dispatch(repo_path=tmp_path, prompt="Run tests")

        assert result.success is False
        assert "Error occurred" in result.output

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_env_scrubbed_on_dispatch(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret", "PATH": "/usr/bin"}):
            d.dispatch(repo_path=tmp_path, prompt="test")

        # Check the env passed to subprocess.run
        call_kwargs = mock_run.call_args[1]
        env_used = call_kwargs["env"]
        assert "ANTHROPIC_API_KEY" not in env_used
        assert "PATH" in env_used

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_standard_repo_gets_allowed_tools(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        result = d.dispatch(repo_path=tmp_path, prompt="test")

        assert result.enforcement == EnforcementMode.ALLOWED_TOOLS
        # Verify command has --allowedTools
        call_args = mock_run.call_args[0][0]
        assert "--allowedTools" in call_args

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_paircoder_repo_gets_contained_auto(self, mock_run, tmp_path):
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        result = d.dispatch(repo_path=tmp_path, prompt="test")

        assert result.enforcement == EnforcementMode.CONTAINED_AUTO

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_dispatch_sets_cwd_to_repo(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        d.dispatch(repo_path=tmp_path, prompt="test")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == tmp_path


# ---------- DispatchConfig ----------


class TestDispatchConfig:
    def test_defaults(self, tmp_path):
        cfg = DispatchConfig(repo_path=tmp_path, prompt="Run tests")
        assert cfg.repo_path == tmp_path
        assert cfg.prompt == "Run tests"
        assert cfg.mode == DispatchMode.SUBPROCESS
        assert cfg.enforcement is None  # auto-detect
        assert cfg.timeout is None
        assert cfg.on_complete is None

    def test_explicit_enforcement(self, tmp_path):
        cfg = DispatchConfig(
            repo_path=tmp_path,
            prompt="Deploy",
            enforcement=EnforcementMode.CONTAINED_AUTO,
        )
        assert cfg.enforcement == EnforcementMode.CONTAINED_AUTO

    def test_timeout_setting(self, tmp_path):
        cfg = DispatchConfig(repo_path=tmp_path, prompt="test", timeout=300)
        assert cfg.timeout == 300


# ---------- DispatchStatus ----------


class TestDispatchStatus:
    def test_status_values(self):
        assert DispatchStatus.RUNNING.value == "running"
        assert DispatchStatus.COMPLETE.value == "complete"
        assert DispatchStatus.FAILED.value == "failed"


# ---------- DispatchResult (extended fields) ----------


class TestDispatchResultExtended:
    def test_result_with_session_fields(self):
        result = DispatchResult(
            success=True,
            output="done",
            enforcement=EnforcementMode.CONTAINED_AUTO,
            method="subprocess",
            session_id="sess-123",
            pid=4567,
            status=DispatchStatus.COMPLETE,
            output_path=Path("/tmp/output.txt"),
        )
        assert result.session_id == "sess-123"
        assert result.pid == 4567
        assert result.status == DispatchStatus.COMPLETE
        assert result.output_path == Path("/tmp/output.txt")

    def test_result_defaults_backward_compat(self):
        """Existing code that doesn't pass new fields still works."""
        result = DispatchResult(
            success=True,
            output="ok",
            enforcement=EnforcementMode.ALLOWED_TOOLS,
            method="subprocess",
        )
        assert result.session_id is None
        assert result.pid is None
        assert result.status is None
        assert result.output_path is None


# ---------- RepoClassifier ----------


class TestRepoClassifier:
    def test_classify_paircoder(self, tmp_path):
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()
        classifier = RepoClassifier()
        repo_type = classifier.classify(tmp_path)
        assert repo_type == RepoType.PAIRCODER

    def test_classify_standard(self, tmp_path):
        (tmp_path / "package.json").touch()
        classifier = RepoClassifier()
        repo_type = classifier.classify(tmp_path)
        assert repo_type == RepoType.STANDARD

    def test_enforcement_for_paircoder(self):
        classifier = RepoClassifier()
        assert classifier.enforcement_for(RepoType.PAIRCODER) == EnforcementMode.CONTAINED_AUTO

    def test_enforcement_for_standard(self):
        classifier = RepoClassifier()
        assert classifier.enforcement_for(RepoType.STANDARD) == EnforcementMode.ALLOWED_TOOLS

    def test_classify_nonexistent_raises(self):
        classifier = RepoClassifier()
        with pytest.raises(DispatchError, match="does not exist"):
            classifier.classify(Path("/nonexistent/path"))


# ---------- dispatch_navigator ----------


class TestDispatchNavigator:
    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_dispatch_navigator_with_config(self, mock_run, tmp_path):
        (tmp_path / ".paircoder").mkdir()
        (tmp_path / ".paircoder" / "config.yaml").touch()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="Navigator done", stderr=""
        )

        d = Dispatcher()
        config = DispatchConfig(repo_path=tmp_path, prompt="Plan sprint")
        result = d.dispatch_navigator(config)

        assert isinstance(result, DispatchResult)
        assert result.success is True
        assert result.output == "Navigator done"
        assert result.enforcement == EnforcementMode.CONTAINED_AUTO

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_dispatch_navigator_explicit_enforcement(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        config = DispatchConfig(
            repo_path=tmp_path,
            prompt="Review code",
            enforcement=EnforcementMode.ALLOWED_TOOLS,
        )
        result = d.dispatch_navigator(config)
        assert result.enforcement == EnforcementMode.ALLOWED_TOOLS

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_dispatch_navigator_sets_status(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=0, stdout="OK", stderr=""
        )

        d = Dispatcher()
        config = DispatchConfig(repo_path=tmp_path, prompt="test")
        result = d.dispatch_navigator(config)
        assert result.status == DispatchStatus.COMPLETE

    @patch("engine.dispatch.dispatcher.subprocess.run")
    def test_dispatch_navigator_failure_status(self, mock_run, tmp_path):
        (tmp_path / ".git").mkdir()

        mock_run.return_value = subprocess.CompletedProcess(
            args=["claude"], returncode=1, stdout="", stderr="crash"
        )

        d = Dispatcher()
        config = DispatchConfig(repo_path=tmp_path, prompt="test")
        result = d.dispatch_navigator(config)
        assert result.status == DispatchStatus.FAILED
        assert result.success is False
