"""JWT token management — extends bpsai-agent-core with org_id support."""

from bpsai_agent_core.auth import TokenManager as _BaseTokenManager


class TokenManager(_BaseTokenManager):
    """TokenManager with org_id support for org-scoped A2A operations."""

    def __init__(
        self, paircoder_api_url: str, license_id: str, operator: str,
        org_id: str | None = None,
    ) -> None:
        super().__init__(paircoder_api_url, license_id, operator)
        self._org_id = org_id

    async def _fetch_token(self) -> str | None:
        """POST to operator-token endpoint with org_id."""
        import httpx

        url = f"{self._api_url}/api/v1/auth/operator-token"
        payload: dict = {"license_id": self._license_id, "operator": self._operator}
        if self._org_id:
            payload["org_id"] = self._org_id
        try:
            resp = await self._http.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._token = data["token"]
            self._expires_at = data["expires_at"]
            import logging
            logging.getLogger(__name__).info("JWT obtained, expires_at=%.0f", self._expires_at)
            return self._token
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            import logging
            logging.getLogger(__name__).warning("Failed to obtain JWT: %s", exc)
            self._token = None
            self._expires_at = 0.0
            return None


__all__ = ["TokenManager"]
