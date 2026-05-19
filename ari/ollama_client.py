"""Thin Ollama HTTP client for chat + embeddings."""
from __future__ import annotations
import json
import time
from typing import Iterable
import urllib.request
import urllib.error

from . import config


def _post(path: str, payload: dict, timeout: int = 600) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{config.OLLAMA_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def chat(prompt: str, system: str | None = None, model: str | None = None) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    out = _post("/api/chat", {
        "model": model or config.LLM_MODEL,
        "messages": msgs,
        "stream": False,
        "options": {
            "temperature": config.LLM_TEMPERATURE,
            "num_ctx": config.LLM_NUM_CTX,
        },
    })
    return out["message"]["content"]


def embed(texts: Iterable[str], model: str | None = None) -> list[list[float]]:
    out = []
    m = model or config.EMBED_MODEL
    for t in texts:
        r = _post("/api/embeddings", {"model": m, "prompt": t})
        out.append(r["embedding"])
    return out
