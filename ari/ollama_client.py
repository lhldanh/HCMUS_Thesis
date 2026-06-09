"""Thin Ollama HTTP client for chat + embeddings, plus OpenAI chat for the
paper-faithful learning phase (methodology induction + action selection
during memory-bank construction)."""
from __future__ import annotations
import json
import os
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
        "think": False,
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


# ---------- OpenAI (used by the learn phase to match paper) ----------

def _post_openai(payload: dict, timeout: int = 120) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY env var not set — required for the GPT-4o learn phase."
        )
    data = json.dumps(payload).encode("utf-8")
    url = getattr(config, "OPENAI_BASE_URL", "https://api.openai.com/v1") \
        + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            # 4xx is non-transient — surface immediately
            if 400 <= he.code < 500 and he.code != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def openai_chat(prompt: str, system: str | None = None,
                model: str | None = None) -> str:
    """OpenAI chat completion (paper uses gpt-4o, temperature=0, seed=319)."""
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    out = _post_openai({
        "model": model or getattr(config, "OPENAI_MODEL", "gpt-4o"),
        "messages": msgs,
        "temperature": getattr(config, "OPENAI_TEMPERATURE", 0.0),
        "seed": getattr(config, "OPENAI_SEED", 319),
    })
    return out["choices"][0]["message"]["content"]


def openai_embed(texts: Iterable[str], model: str | None = None) -> list[list[float]]:
    """OpenAI embeddings — batched. Defaults to text-embedding-3-small."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY env var not set — required for OpenAI embeddings."
        )
    m = model or getattr(config, "OPENAI_EMBED_MODEL", "text-embedding-3-small")
    texts = list(texts)
    if not texts:
        return []
    url = getattr(config, "OPENAI_BASE_URL", "https://api.openai.com/v1") + "/embeddings"
    data = json.dumps({"model": m, "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
                return [d["embedding"] for d in payload["data"]]
        except urllib.error.HTTPError as he:
            if 400 <= he.code < 500 and he.code != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")
