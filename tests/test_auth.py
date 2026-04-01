"""Tests for JWT token management (auth.py)."""

import time

import httpx
import pytest
import respx

from computer.auth import TokenManager


API_URL = "http://localhost:8080"
TOKEN_ENDPOINT = f"{API_URL}/api/v1/auth/operator-token"


class TestTokenFetch:
    """Test obtaining a JWT from paircoder_api."""

    @respx.mock
    async def test_fetch_token_success(self):
        expires = time.time() + 3600
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json={
                "token": "jwt-abc",
                "expires_at": expires,
                "tier": "pro",
                "operator": "mike",
            })
        )
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        token = await mgr.get_token()
        assert token == "jwt-abc"

    @respx.mock
    async def test_fetch_sends_correct_payload(self):
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json={
                "token": "jwt-abc",
                "expires_at": time.time() + 3600,
                "tier": "pro",
                "operator": "mike",
            })
        )
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        await mgr.get_token()
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["license_id"] == "lic-123"
        assert body["operator"] == "mike"


class TestTokenCaching:
    """Test that tokens are cached and not re-fetched until expired."""

    @respx.mock
    async def test_cached_token_reused(self):
        route = respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json={
                "token": "jwt-abc",
                "expires_at": time.time() + 3600,
                "tier": "pro",
                "operator": "mike",
            })
        )
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        t1 = await mgr.get_token()
        t2 = await mgr.get_token()
        assert t1 == t2
        assert len(route.calls) == 1  # only one HTTP call

    @respx.mock
    async def test_expired_token_refreshed(self):
        # First call returns token expiring in the past
        call_count = 0

        def handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={
                    "token": "jwt-old",
                    "expires_at": time.time() - 10,  # already expired
                    "tier": "pro",
                    "operator": "mike",
                })
            return httpx.Response(200, json={
                "token": "jwt-new",
                "expires_at": time.time() + 3600,
                "tier": "pro",
                "operator": "mike",
            })

        respx.post(TOKEN_ENDPOINT).mock(side_effect=handler)
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        t1 = await mgr.get_token()
        assert t1 == "jwt-old"
        # Second call should refresh because token is expired
        t2 = await mgr.get_token()
        assert t2 == "jwt-new"
        assert call_count == 2


class TestTokenFetchFailure:
    """Test behavior when token fetch fails."""

    @respx.mock
    async def test_fetch_failure_returns_none(self):
        respx.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        token = await mgr.get_token()
        assert token is None

    @respx.mock
    async def test_network_error_returns_none(self):
        respx.post(TOKEN_ENDPOINT).mock(side_effect=httpx.ConnectError("refused"))
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        token = await mgr.get_token()
        assert token is None


class TestTokenManagerClose:
    """Test cleanup."""

    async def test_close(self):
        mgr = TokenManager(
            paircoder_api_url=API_URL,
            license_id="lic-123",
            operator="mike",
        )
        await mgr.close()  # should not raise
