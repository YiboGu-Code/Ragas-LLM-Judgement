from __future__ import annotations

import asyncio
import os
from typing import Any

from openai import AsyncOpenAI
from ragas.embeddings.base import BaseRagasEmbeddings
from ragas.llms import llm_factory

from app.core.dotenv import load_dotenv

def _create_ark_client(*, api_key: str):
    from volcenginesdkarkruntime import Ark

    return Ark(api_key=api_key)


def _extract_embedding_vector(resp: Any) -> list[float]:
    data = getattr(resp, "data", None)
    if data is None and isinstance(resp, dict):
        data = resp.get("data")
    if data is None:
        embedding = getattr(resp, "embedding", None)
        if embedding is None and isinstance(resp, dict):
            embedding = resp.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("invalid embeddings response: missing data")
        return [float(x) for x in embedding]

    if isinstance(data, list):
        if not data:
            raise ValueError("invalid embeddings response: missing data")
        first = data[0]
        embedding = getattr(first, "embedding", None)
        if embedding is None and isinstance(first, dict):
            embedding = first.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise ValueError("invalid embeddings response: missing embedding")
        return [float(x) for x in embedding]

    embedding = getattr(data, "embedding", None)
    if embedding is None and isinstance(data, dict):
        embedding = data.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError("invalid embeddings response: missing embedding")
    return [float(x) for x in embedding]


class ArkMultimodalEmbeddings(BaseRagasEmbeddings):
    def __init__(self, *, client: Any, model: str):
        super().__init__(cache=None)
        self._client = client
        self._model = model

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self.embed_query(text, **kwargs)

    async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
        return await self.aembed_query(text, **kwargs)

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        resp = self._client.multimodal_embeddings.create(
            model=self._model,
            input=[{"type": "text", "text": text}],
            **kwargs,
        )
        return _extract_embedding_vector(resp)

    def embed_documents(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return [self.embed_query(text, **kwargs) for text in texts]

    async def aembed_query(self, text: str, **kwargs: Any) -> list[float]:
        return await asyncio.to_thread(self.embed_query, text, **kwargs)

    async def aembed_documents(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts, **kwargs)


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
            load_dotenv()
            api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"missing environment variable {api_key_env}")

        self._base_url = base_url or "https://ark.cn-beijing.volces.com/api/v3"
        self._model = model or "doubao-seed-2-0-mini-260428"
        self._embedding_model = embedding_model or "doubao-embedding-vision-251215"
        self._client = AsyncOpenAI(base_url=self._base_url, api_key=api_key)
        self._api_key = api_key

    def get_ragas_llm(self):
        return llm_factory(self._model, provider="openai", client=self._client)

    def get_ragas_embeddings(self):
        if not self._embedding_model:
            raise ValueError("missing provider embedding_model")
        ark = _create_ark_client(api_key=self._api_key)
        return ArkMultimodalEmbeddings(client=ark, model=self._embedding_model)

    async def chat(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        resp = await self._client.responses.create(model=self._model, input=messages, **kwargs)
        text = getattr(resp, "output_text", None)
        return {"text": text, "raw": resp.model_dump()}

    async def embed(self, *, texts: list[str], **kwargs: Any) -> list[list[float]]:
        embeddings = self.get_ragas_embeddings()
        return await embeddings.aembed_documents(texts, **kwargs)
