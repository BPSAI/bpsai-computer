"""Tests for CDF.2: Credential scrubbing gaps."""

from computer.scrubber import scrub_credentials
from computer.lifecycle import extract_session_id


# ── New scrubber patterns ─────────────────────────────────────────


class TestNewScrubberPatterns:
    """Test that newly added scrubber patterns catch their targets."""

    def test_scrubs_github_pat_ghp(self):
        text = "Using token ghp_1234567890abcdefABCDEF1234567890abcd"
        result = scrub_credentials(text)
        assert "ghp_" not in result
        assert "REDACTED" in result

    def test_scrubs_github_pat_prefix(self):
        text = "Token github_pat_1234567890abcdefABCDEF1234567890a"
        result = scrub_credentials(text)
        assert "github_pat_" not in result
        assert "REDACTED" in result

    def test_scrubs_gcp_oauth_token(self):
        text = "Authorization: ya29.a0AfH6SMBxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = scrub_credentials(text)
        assert "ya29." not in result
        assert "REDACTED" in result

    def test_scrubs_openai_key(self):
        text = "OPENAI_API_KEY=sk-proj-1234567890abcdefghij"
        result = scrub_credentials(text)
        assert "sk-proj-" not in result
        assert "REDACTED" in result

    def test_scrubs_openai_key_sk_prefix(self):
        text = "key is sk-1234567890abcdefghijklmnopqr"
        result = scrub_credentials(text)
        assert "sk-1234567890" not in result
        assert "REDACTED" in result

    def test_scrubs_url_embedded_credentials(self):
        text = "connecting to https://admin:s3cret@db.example.com/mydb"
        result = scrub_credentials(text)
        assert "admin:s3cret" not in result
        assert "REDACTED" in result

    def test_scrubs_url_embedded_credentials_http(self):
        text = "http://user:password123@redis.local:6379"
        result = scrub_credentials(text)
        assert "user:password123" not in result
        assert "REDACTED" in result

    def test_preserves_normal_urls(self):
        text = "Fetching https://api.example.com/v1/status"
        result = scrub_credentials(text)
        assert result == text


# ── stdout_lines scrubbing ────────────────────────────────────────


class TestStdoutLinesScrubbed:
    """stdout_lines must store scrubbed content (or be cleared after extract)."""

    def test_stdout_lines_do_not_contain_raw_credentials(self):
        from computer.config import DaemonConfig
        from computer.streamer import OutputStreamer
        from unittest.mock import AsyncMock

        config = DaemonConfig(
            operator="mike", workspace="bpsai",
            workspace_root="/tmp", a2a_url="http://localhost:9999",
        )
        a2a = AsyncMock()
        streamer = OutputStreamer(session_id="sess-1", a2a=a2a, config=config)
        streamer.add_line("key=sk-ant-abcdefghijklmnop", stream="stdout")
        streamer.add_line("normal line", stream="stdout")

        for line in streamer.stdout_lines:
            assert "sk-ant" not in line


# ── extract_session_id regex cap ──────────────────────────────────


class TestExtractSessionIdCap:
    """extract_session_id regex should cap captured ID at 256 chars."""

    def test_overlong_session_id_in_stdout_not_extracted(self):
        long_id = "a" * 300
        lines = [f"Session: {long_id}"]
        result = extract_session_id(lines, fallback_id="fallback-id")
        # Should use fallback since the extracted ID is too long
        assert len(result) <= 256
