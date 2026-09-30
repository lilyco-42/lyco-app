"""Verifier (OODA Re-observe).

Ported from lyco-model/rag_loop.py after a day of measured fixes there; the
keyword-overlap rule alone only proves the model *copied*, not that it copied
*right*, so:

  - every precision claim (decimals, percentages, 3+ digits, or a number glued
    to a unit) must exist in the evidence, matched as a token, not a substring
  - an answer must touch the question's content terms, and 2-char Chinese words
    like 量化/缺点 count (they are what a correct answer repeats)
  - "no evidence" is only acceptable with an explicit decline, and declines
    come in more than one phrasing
  - the hits sample is sorted: set order is hash-randomized per process, so an
    unsorted record cannot be replayed
"""
import re

from core.retrievers import RETRIEVE_STOP, tokens

STOPWORDS = set("什么是为什么如何怎么的了着是在与和或一个以及"
                "什么是吗呢吧啊呀")

UNIT_TAIL = (r"\s*-?\s*(?:%|％|bits?|bytes?|[KMGT]i?B|t/s|tok(?:en)?s?|"
             r"ms|sec(?:ond)?s?|s\b|秒|分钟|小时|天|周|个月|年|倍|x\b)")
UNIT_RE = re.compile(UNIT_TAIL)
FLAT = re.compile(r"[\s\-]+")

# Evidence-free claims we refuse to let through on a direct turn as well.
DECLINE = ["不知道", "不清楚", "不了解", "没有相关", "没有关于",
           "没有足够", "没有具体", "无法确定", "无法回答", "请提供", "提供更多",
           "尚未", "没听说过"]

UNSUP_TOL = 1     # evidence-free latin tokens we tolerate in an answer


def latin_terms(text):
    return set(re.findall(r"[A-Za-z][A-Za-z0-9_+#.\-]{2,}", text))


def claim_matches(text):
    """(number, number+unit span) for every precision claim in text."""
    out = []
    for m in re.finditer(r"\d+(?:[.,]\d+)?%?", text):
        n = m.group(0)
        unit = UNIT_RE.match(text[m.end():m.end() + 10])
        if re.search(r"[.,%]\d|\d{3}", n) or n.endswith("%") or unit:
            out.append((n, n + (unit.group(0) if unit else "")))
    return out


def digit_claims(text):
    return set(n for n, _ in claim_matches(text))


def unsourced_claims(text, hay):
    """Claim numbers that `hay` does not support.

    Supported means: the number appears as its own token (letters glued to it
    do not count -- `UINT8` in a tensor-type list must not back an 8-bit
    claim), or the number+unit span matches once whitespace/hyphens are folded
    away (evidence `400MB` must support an answer saying `400 MB`)."""
    flat_hay = FLAT.sub("", hay)
    bad = set()
    for num, span in claim_matches(text):
        if re.search(rf"(?<![\w.]){re.escape(num)}(?![\w.])", hay):
            continue
        if span and FLAT.sub("", span) in flat_hay:
            continue
        bad.add(num)
    return sorted(bad)


def relevance_terms(question):
    """Content terms an answer must touch. tokens() already emits Chinese
    bigrams; RETRIEVE_STOP drops the question words, so what is left is what
    the question is actually about."""
    return [t for t in tokens(question)
            if len(t) >= 2 and t not in RETRIEVE_STOP]


def verify(question, evidence, response, searched=True, anchors=None,
           prior_evidence=()):
    if not searched:
        # A direct turn is not evidence-grounded, but it still must not hand
        # out made-up precision.
        pool = question + "\n" + "\n".join(prior_evidence)
        fab = unsourced_claims(response, pool)
        return {"pass": not fab,
                "reason": "direct" if not fab else "direct-unsourced-numbers",
                "invented_numbers": fab}
    ev_all = list(evidence) + list(prior_evidence)
    if not ev_all:
        said = next((d for d in DECLINE if d in response), None)
        return {"pass": said is not None, "reason": "no-evidence",
                "decline": said or ""}
    hay = "\n".join(ev_all) + "\n" + question
    hay_l = hay.lower()

    words = set()
    for ev in ev_all:
        for w in re.findall(r"[\u4e00-\u9fffA-Za-z]{2,12}", ev):
            if w not in STOPWORDS:
                words.add(w)
    hits = [w for w in sorted(words) if w in response]

    unsup = sorted(t for t in latin_terms(response) if t.lower() not in hay_l)
    fab_num = unsourced_claims(response, hay)

    anch = anchors if anchors is not None else relevance_terms(question)
    anch = [a for a in anch if len(a) >= 2]
    rel = any(a in response or a.lower() in response.lower() for a in anch)

    reasons = []
    if len(hits) < 2:
        reasons.append("low-overlap")
    if not rel:
        reasons.append("off-topic")
    if fab_num:
        reasons.append("invented-numbers")
    if len(unsup) > UNSUP_TOL:
        reasons.append("unsupported-terms")
    return {"pass": not reasons,
            "reason": ",".join(reasons) or f"overlap={len(hits)}",
            "overlap": len(hits), "hits": hits[:8],
            "invented_numbers": fab_num,
            "unsupported_terms": unsup[:8],
            "on_topic": rel}
