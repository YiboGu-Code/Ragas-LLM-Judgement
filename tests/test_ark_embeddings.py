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
