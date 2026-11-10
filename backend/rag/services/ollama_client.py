"""Thin client for the local Ollama server (embeddings + chat)."""
import requests
from django.conf import settings


class OllamaError(Exception):
    pass


def _call(method, path, payload=None, timeout=300):
    try:
        r = requests.request(method, f"{settings.OLLAMA_URL}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        raise OllamaError(str(exc)) from exc


def embed(texts):
    """Return one embedding vector per input text."""
    return _call("POST", "/api/embed", {"model": settings.EMBED_MODEL, "input": texts}, 120)["embeddings"]


def chat(messages):
    data = _call("POST", "/api/chat", {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1},
    })
    return data["message"]["content"].strip()


def models():
    return [m["name"] for m in _call("GET", "/api/tags", timeout=5).get("models", [])]
