"""JWT token management: obtain and cache tokens from paircoder_api."""

from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger(__name__)


class TokenManager:
    """Obtains and caches JWT from paircoder_api operator-token endpoint."""

    def __init__(self, paircoder_api_url: str, license_id: str, operator: str) -> None:
        self._api_url = paircoder_api_url.rstrip("/")
        self._license_id = license_id
        self._operator = operator
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0),
        )

    async def get_token(self) -> str | None:
        """Return cached token or fetch a new one. Returns None on failure."""
        if self._token and time.time() < (self._expires_at - 60):
            return self._token
        return await self._fetch_token()

    async def _fetch_token(self) -> str | None:
        """POST to operator-token endpoint and cache the result."""
        url = f"{self._api_url}/api/v1/auth/operator-token"
        payload = {"license_id": self._license_id, "operator": self._operator}
        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._token = data["token"]
            self._expires_at = data["expires_at"]
            log.info("JWT obtained, expires_at=%.0f", self._expires_at)
            return self._token
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("Failed to obtain JWT: %s", exc)
            self._token = None
            self._expires_at = 0.0
            return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
