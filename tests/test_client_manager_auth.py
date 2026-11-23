import core.api.client_manager as client_manager
from core.api.client_manager import GeminiClientManager
from core.api.key_pool import APIKeyPool


class FakeClientError(Exception):
    pass


class BadModels:
    def generate_content_stream(self, **_kwargs):
        raise FakeClientError("401 UNAUTHENTICATED")


class GoodModels:
    def generate_content_stream(self, **_kwargs):
        chunk = type("Chunk", (), {})()
        part = type("Part", (), {})()
        part.inline_data = type("Inline", (), {"data": b"audio"})()
        chunk.parts = [part]
        return iter([chunk])


class Client:
    def __init__(self, models):
        self.models = models


def test_stream_retry_skips_key_that_returns_unauthenticated(monkeypatch):
    """A bad API key must be excluded for the requested model so a usable key can continue the job."""
    pool = APIKeyPool(keys=["bad-key", "good-key"])
    manager = GeminiClientManager(key_pool=pool)
    clients = {"bad-key": Client(BadModels()), "good-key": Client(GoodModels())}

    monkeypatch.setattr(client_manager, "ClientError", FakeClientError)
    monkeypatch.setattr(manager, "_get_client_for_key", lambda key: clients[key])

    audio = manager.execute_stream_with_retry(
        model="gemini-2.5-flash-preview-tts",
        contents=[],
        config=None,
        max_retries=2,
    )

    assert audio == b"audio"
    assert "gemini-2.5-flash-preview-tts" in pool.keys[0].exhausted_models
    assert pool.keys[1].successful_calls == 1
