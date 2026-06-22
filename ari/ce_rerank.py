"""Inference-time cross-encoder rerank.

torch/transformers/pyvi được nạp lười (chỉ khi `USE_CROSS_ENCODER=True` và
`rerank`/`score` được gọi thật). Test inject `_model_predict` nên không cần
model.
"""
from __future__ import annotations

from . import config
from . import ce_serialize as S

_MODEL = None


def _load():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import CrossEncoder
        _MODEL = CrossEncoder(str(config.CE_MODEL_DIR),
                              max_length=config.CE_MAX_LEN)
    return _MODEL


def _model_predict(pairs):
    return _load().predict(pairs)


def score(question, steps, actions):
    """Điểm liên quan cho từng action theo (question, history)."""
    pairs = []
    for a in actions:
        ctx, act = S.make_pair(question, steps, a)
        pairs.append([S.segment(ctx), S.segment(act)])
    return list(_model_predict(pairs))


def rerank(question, steps, actions, top=config.TOP_K_ACTIONS):
    """Sắp xếp actions giảm dần theo điểm cross-encoder, giữ `top` đầu."""
    if not actions:
        return actions
    scores = score(question, steps, actions)
    order = sorted(range(len(actions)), key=lambda i: -scores[i])
    return [actions[i] for i in order[:top]]
