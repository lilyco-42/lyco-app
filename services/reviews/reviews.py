"""services.reviews — rank shops by aggregated review evidence.

services/poi answers "how many shops nearby"; services.reviews answers
"which shop is best". Each shop gets its own Chinese review query run
through the core RAG loop (core.loop.answer); ranking is evidence-first
(verified-first, then evidence count desc). Never invent reviews: a shop
with no evidence / failed verify simply ranks last.

Function interface only (services 层只暴露函数接口, 见 docs/ARCHITECTURE.md):
- rank_shops(pois, question=None, answer_fn=None) -> list[dict]
"""
from __future__ import annotations

from typing import Any

DEFAULT_QUESTION = "哪家店最好？"


def _normalize(value: Any) -> str:
    """Amap quirk: missing fields come back as []; normalize to str."""
    if isinstance(value, (list, tuple)):
        value = "".join(map(str, value))
    return str(value or "").strip()


def _shop_query(question: str, name: str, address: str) -> str:
    """Per-shop review query (Chinese, built from name + address)."""
    return (f"关于「{question}」请查找顾客对{name}（地址：{address}）"
            f"的真实评价，不要编造评价。")


def rank_shops(pois, question=None, answer_fn=None):
    """Rank POI shops by aggregated review evidence via the core RAG loop.

    pois: list of dicts shaped like services.poi nearby_search output
          (name / address / location keys; address may be [] per Amap).
    question: overall question; None -> DEFAULT_QUESTION (Chinese).
    answer_fn: question str -> core.loop.answer-shaped dict. Defaults to
          core.loop.answer; injectable for offline tests (no network/LLM).

    Returns a list of dicts with name / address / reason / summary keys,
    sorted verified-first, then by evidence count desc. Shops without a
    non-empty name are skipped.
    """
    if answer_fn is None:
        from core.loop import answer as answer_fn
    q = question if question else DEFAULT_QUESTION
    records = []
    for poi in pois or []:
        name = _normalize(poi.get("name"))
        if not name:
            continue  # no name -> no queryable shop
        address = _normalize(poi.get("address"))
        r = answer_fn(_shop_query(q, name, address))
        v = r.get("verify") or {}
        records.append({
            "name": name,
            "address": address,
            "evidence_count": len(r.get("evidence") or []),
            "verify_pass": bool(v.get("pass")),
            "reason": str(v.get("reason") or ""),
            "summary": str(r.get("response") or "").strip(),
        })
    records.sort(key=lambda rec: (0 if rec["verify_pass"] else 1,
                                  -rec["evidence_count"]))
    return [{"name": rec["name"], "address": rec["address"],
             "reason": rec["reason"], "summary": rec["summary"]}
            for rec in records]
