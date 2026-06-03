from __future__ import annotations

import httpx


class HttpSUTAdapter:
    name = "http"

    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def execute(self, *, record: dict, provider) -> dict:
        resp = await self._client.post("/execute", json={"record": record})
        resp.raise_for_status()
        return resp.json()
