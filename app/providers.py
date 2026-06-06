from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI
from ragas.embeddings.openai_provider import OpenAIEmbeddings
from ragas.llms import InstructorLLM


class ArkProvider:
    name = "ark"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        api_key_env: str = "ARK_API_KEY",
    ) -> None:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"missing environment variable {api_key_env}")

        self._base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
        self._model = model or "doubao-seed-2-0-mini-260428"
        self._embedding_model = embedding_model
        self._client = AsyncOpenAI(base_url=self._base_url, api_key=api_key)

    def get_ragas_llm(self):
        return InstructorLLM(client=self._client, model=self._model, provider="openai")

    def get_ragas_embeddings(self):
        if not self._embedding_model:
            raise ValueError("missing provider embedding_model")
        return OpenAIEmbeddings(client=self._client, model=self._embedding_model)

    async def chat(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        resp = await self._client.responses.create(model=self._model, input=messages, **kwargs)
        text = getattr(resp, "output_text", None)
        return {"text": text, "raw": resp.model_dump()}

    async def embed(self, *, texts: list[str], **kwargs: Any) -> list[list[float]]:
        if not self._embedding_model:
            raise ValueError("missing provider embedding_model")
        resp = await self._client.embeddings.create(model=self._embedding_model, input=texts, **kwargs)
        return [d.embedding for d in resp.data]
