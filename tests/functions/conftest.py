"""Test doubles for the DISC Risk Gate's `request` seam.

The classifier is faked at the HTTP boundary with `httpx.MockTransport`, which
is the pattern to reuse for future tool tests that call external services.
"""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from dartmouth_chat_tools.functions.disc_risk_gate import Filter

CATEGORIES = [
    "government_id",
    "personal_details",
    "ferpa",
    "hipaa",
    "pci",
    "glba",
    "cui",
]


def clef_response(
    flags: dict[str, float] | None = None,
    disc_level: float = 0.1,
    input_tokens: int = 1000,
) -> dict:
    """A Clef `/v1/systemone` response, in the shape recorded in #16."""
    flags = flags or {}
    answers: dict = {}
    for name in CATEGORIES:
        p = flags.get(name, 0.02)
        answers[name] = {
            "type": "noul",
            "noul": p,
            "probabilities": {"yes": p, "no": 1 - p},
            "confidence": max(p, 1 - p),
        }
    answers["disc_level"] = {
        "type": "score",
        "score": disc_level,
        "confidence": 0.9,
        "legend": {"0": "...", "1": "...", "2": "...", "3": "..."},
        "probabilities": {"0": 0.25, "1": 0.25, "2": 0.25, "3": 0.25},
    }
    return {
        "model": "clef",
        "answers": answers,
        "usage": {"input_tokens": input_tokens, "output_tokens": 0},
        "id": "decision-test",
        "object": "structured_decision",
        "created": 1793321714,
        "diagnostics": {},
    }


class FakeClassifier:
    """Answers each message by looking up markers in its `state`.

    `rules` maps a substring to the response returned when the classified
    message contains it; anything else gets a harmless verdict.
    """

    def __init__(self):
        self.rules: list[tuple[str, dict]] = []
        self.requests: list[dict] = []
        self.status = 200
        self.raw_body: bytes | None = None
        self.delay = 0.0

    def flag(self, marker: str, **kwargs) -> None:
        self.rules.append((marker, clef_response(**kwargs)))

    async def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        self.requests.append(payload)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raw_body is not None:
            return httpx.Response(self.status, content=self.raw_body)
        if self.status != 200:
            return httpx.Response(
                self.status,
                json={
                    "error": {
                        "message": f"Invalid request: input_value={payload['state']!r}",
                        "type": "invalid_request_error",
                    }
                },
            )
        for marker, response in self.rules:
            if marker in payload["state"]:
                return httpx.Response(200, json=response)
        return httpx.Response(200, json=clef_response())

    @property
    def states(self) -> list[str]:
        return [r["state"] for r in self.requests]


class FakeEventCall:
    """Records confirmation dialogs and answers them with `result`."""

    def __init__(self, result=True):
        self.result = result
        self.dialogs: list[dict] = []

    async def __call__(self, event: dict):
        self.dialogs.append(event)
        return self.result


class FakeEventEmitter:
    def __init__(self):
        self.events: list[dict] = []

    async def __call__(self, event: dict):
        self.events.append(event)

    @property
    def descriptions(self) -> list[str]:
        return [e["data"].get("description", "") for e in self.events]


def cloud_model(model_id: str = "openai.gpt-5") -> dict:
    return {"id": model_id, "tags": [{"name": "cloud"}], "info": {"meta": {}}}


def local_model(model_id: str = "dartmouth.llama") -> dict:
    return {"id": model_id, "tags": [{"name": "local"}], "info": {"meta": {}}}


def make_request(*models: dict) -> SimpleNamespace:
    """A stand-in for the FastAPI request, exposing the app's model registry."""
    registry = {m["id"]: m for m in models}
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(MODELS=registry)))


def user(text: str) -> dict:
    return {"role": "user", "content": text}


@pytest.fixture(autouse=True)
def litellm_env(monkeypatch):
    monkeypatch.setenv("LITELLM_PROXY_BASE_URL", "https://litellm.example.com")
    monkeypatch.setenv("LITELLM_PROXY_API_KEY", "sk-test")


@pytest.fixture
def classifier() -> FakeClassifier:
    return FakeClassifier()


@pytest.fixture
def gate(classifier) -> Filter:
    return Filter(transport=httpx.MockTransport(classifier.handler))


@pytest.fixture
def event_call() -> FakeEventCall:
    return FakeEventCall()


@pytest.fixture
def emitter() -> FakeEventEmitter:
    return FakeEventEmitter()


@pytest.fixture
def run(gate, event_call, emitter):
    """Call `gate.request` the way Open WebUI does, with a cloud model by default."""

    async def _run(messages, model=None, registry=(), **overrides):
        model = model or cloud_model()
        params = dict(
            body={"model": model["id"], "messages": messages},
            __model__=model,
            __request__=make_request(model, *registry),
            __event_emitter__=emitter,
            __event_call__=event_call,
        )
        params.update(overrides)
        return await gate.request(**params)

    return _run
