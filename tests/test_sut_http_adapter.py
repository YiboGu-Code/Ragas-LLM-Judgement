import json

import httpx
import pytest

from app.sut.http_adapter import HttpSUTAdapter


class MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        content = json.dumps({"output": {"final": "ok"}, "trace": {"messages": []}}).encode("utf-8")
        return httpx.Response(200, content=content, request=request)


@pytest.mark.anyio
async def test_http_sut_adapter_returns_trace():
    adapter = HttpSUTAdapter(base_url="http://sut", timeout_seconds=5)
    adapter._client = httpx.AsyncClient(transport=MockTransport(), base_url="http://sut")
    trace = await adapter.execute(record={"type": "prompt", "input": {"user_input": "hi"}}, provider=None)
    assert trace["output"]["final"] == "ok"
