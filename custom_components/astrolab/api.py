"""A small client for the Astrolab REST API."""

from __future__ import annotations

from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=25)


class AstrolabError(Exception):
    """Astrolab could not be reached, or answered with an error."""


class AstrolabClient:
    def __init__(self, session: aiohttp.ClientSession, url: str) -> None:
        self._session = session
        self.url = normalize_url(url)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with self._session.request(method, f"{self.url}{path}", timeout=TIMEOUT, **kwargs) as resp:
                if resp.status >= 400:
                    raise AstrolabError(f"{path}: HTTP {resp.status}")
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise AstrolabError(f"{path}: {exc}") from exc

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/api/health")

    async def scope(self) -> dict[str, Any]:
        return await self._request("GET", "/api/scope")

    async def weather(self) -> dict[str, Any]:
        return await self._request("GET", "/api/scope/weather")

    async def morning(self) -> dict[str, Any]:
        return await self._request("GET", "/api/morning")

    async def tonight(self) -> dict[str, Any]:
        return await self._request("GET", "/api/tonight")

    async def system(self) -> dict[str, Any]:
        return await self._request("GET", "/api/system")

    async def set_auto(self, enabled: bool) -> dict[str, Any]:
        # Leaving out `targets` keeps the target list as it is.
        return await self._request("PUT", "/api/scope/auto", json={"enabled": enabled})


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url
