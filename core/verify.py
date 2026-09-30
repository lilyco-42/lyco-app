"""Verifier: keyword overlap between evidence and response (OODA
Re-observe)."""
import re

STOPWORDS = set("什么是为什么如何怎么的了着是在与和或一个以及"
                "什么是吗呢吧啊呀")


def verify(question, evidence, response, searched=True):
    """OODA Re-observe: keyword overlap between evidence and response."""
    if not searched:
        return {"pass": True, "reason": "direct"}
    if not evidence:
        return {"pass": "不知道" in response, "reason": "no-evidence"}
    words = set()
    for ev in evidence:
        for w in re.findall(r"[\u4e00-\u9fffA-Za-z]{2,12}", ev):
            if w not in STOPWORDS:
                words.add(w)
    hits = [w for w in words if w in response]
    return {"pass": len(hits) >= 2, "reason": f"overlap={len(hits)}",
            "hits": hits[:8]}
