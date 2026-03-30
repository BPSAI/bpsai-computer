"""Tests for credential scrubbing."""

from computer.scrubber import scrub_credentials


class TestScrubCredentials:
    """Test credential scrubbing on output text."""

    def test_scrubs_api_keys(self):
        text = "Using key sk-ant-api03-abc123xyz456 for auth"
        result = scrub_credentials(text)
        assert "sk-ant-api03-abc123xyz456" not in result
        assert "***" in result

    def test_scrubs_bearer_tokens(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature"
        result = scrub_credentials(text)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_scrubs_generic_secrets(self):
        text = 'password = "super_secret_123"\napi_key = "AKIAIOSFODNN7EXAMPLE"'
        result = scrub_credentials(text)
        assert "super_secret_123" not in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_preserves_normal_text(self):
        text = "Audit complete. Found 3 issues in src/main.py"
        result = scrub_credentials(text)
        assert result == text

    def test_scrubs_env_var_patterns(self):
        text = "export ANTHROPIC_API_KEY=sk-ant-1234567890abcdef"
        result = scrub_credentials(text)
        assert "sk-ant-1234567890abcdef" not in result

    def test_handles_empty_string(self):
        assert scrub_credentials("") == ""
