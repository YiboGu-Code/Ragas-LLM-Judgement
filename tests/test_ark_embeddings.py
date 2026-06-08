import types

import app.providers as providers


def test_ark_multimodal_embeddings_extracts_vector():
    class DummyMulti:
        def __init__(self):
            self.calls = []

        def create(self, *, model, input, **kwargs):
            self.calls.append({"model": model, "input": input, "kwargs": kwargs})

            class Item:
                embedding = [0.1, 0.2, 0.3]

            return types.SimpleNamespace(data=[Item()])

    dummy = types.SimpleNamespace(multimodal_embeddings=DummyMulti())
    emb = providers.ArkMultimodalEmbeddings(client=dummy, model="doubao-embedding-vision-251215")
    vec = emb.embed_text("天很蓝，海很深")
    assert vec == [0.1, 0.2, 0.3]


def test_ark_provider_ragas_llm_client_is_instructor_patched(monkeypatch):
    from openai import AsyncOpenAI
    import instructor

    captured = {}

    def fake_from_openai(client, mode):
        captured["mode"] = mode
        return object()

    monkeypatch.setattr(instructor, "from_openai", fake_from_openai)
    monkeypatch.setenv("ARK_API_KEY_TEST", "dummy")
    monkeypatch.setenv("ARK_MODEL", "deepseek-v3-2-251201")
    monkeypatch.delenv("ARK_INSTRUCTOR_MODE", raising=False)
    p = providers.ArkProvider(api_key_env="ARK_API_KEY_TEST")
    llm = p.get_ragas_llm()

    client = getattr(llm, "client", None)
    assert client is not None
    assert not isinstance(client, AsyncOpenAI)
    assert captured["mode"] == instructor.Mode.TOOLS


def test_extract_embedding_vector_supports_object_data():
    class Data:
        embedding = [0.1, 0.2, 0.3]

    resp = types.SimpleNamespace(data=Data())
    vec = providers._extract_embedding_vector(resp)
    assert vec == [0.1, 0.2, 0.3]


def test_ark_multimodal_embeddings_implements_embed_query_and_documents():
    class DummyMulti:
        def create(self, *, model, input, **kwargs):
            class Data:
                embedding = [0.1, 0.2, 0.3]

            return types.SimpleNamespace(data=Data())

    dummy = types.SimpleNamespace(multimodal_embeddings=DummyMulti())
    emb = providers.ArkMultimodalEmbeddings(client=dummy, model="doubao-embedding-vision-251215")
    assert emb.embed_query("q") == [0.1, 0.2, 0.3]
    assert emb.embed_documents(["a", "b"]) == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
