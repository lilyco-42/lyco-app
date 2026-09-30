"""test_core_offline: the core loop's logic without a model and without the
network. test_core.py is the machine-local smoke test that needs llama-cli plus
the local kb; this one is what CI can run.

Covers the four fixes ported from lyco-model today:
  router  - factual asks route even with no 什么/为什么 phrase; chit-chat stays direct
  verify  - precision claims (units, percentages) must be sourced, token not substring
  deepwiki- rate limits get backoff; error bodies are never evidence
  sources - Wikipedia is gone

Run: python test_core_offline.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core  # noqa: E402
from core import loop  # noqa: E402
from core.retrievers import deepwiki as dw  # noqa: E402
from core.router import need_search, needs_evidence, source_order  # noqa: E402
from core.verify import (digit_claims, relevance_terms,  # noqa: E402
                         unsourced_claims, verify)

PASSED = []


def ok(name):
    PASSED.append(name)
    print(f"PASS {name}")


# -- router -----------------------------------------------------------------

def test_cue_routing():
    assert needs_evidence("量化有什么缺点？") is True, "缺点 must route"
    assert needs_evidence("会不会影响精度？") is True, "会不会 must route"
    assert needs_evidence("给我讲个笑话") is False, "chit-chat must stay direct"
    assert needs_evidence("它会让模型跑得更快吗？") is False, \
        "a bare referent with no topic has nothing to search for"
    assert needs_evidence("它会让模型跑得更快吗？", topic="什么是 GGUF？") is True, \
        "with a topic, a referent question needs evidence"
    assert needs_evidence("精度会掉吗？", topic="什么是 GGUF？") is True, \
        "a yes/no question inside a knowledge conversation needs evidence"
    assert need_search("什么是 GGUF？") is True
    ok("router: cues and referents route, chit-chat stays direct")


def test_no_wikipedia_source():
    for q in ("什么是 GGUF？", "Rust 日报今天有什么", "mpkg 记忆包是什么"):
        assert "wiki" not in source_order(q), f"wiki must be gone: {q}"
        assert "deepwiki" in source_order(q)
    assert not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "core", "retrievers", "wiki.py")), \
        "the dead Wikimedia retriever must not linger"
    ok("sources: Wikipedia dropped from every order, file removed")


# -- verify -----------------------------------------------------------------

EVIDENCE = ["【DeepWiki:ggml-org/llama.cpp】Q4_K_M 是 4 bit 的 K-quant 超级块格式，"
            "困惑度增加 +0.1754，文件约 400MB。"]


def test_claims_must_be_sourced():
    good = "Q4_K_M 是 4 bit 量化档，困惑度约 +0.1754，文件约 400 MB。"
    v = verify("Q4_K_M 是什么？", EVIDENCE, good)
    assert v["pass"] is True, f"correct answer must pass: {v}"
    assert v["invented_numbers"] == []

    bad = "量化把浮点转成低精度整数（如 8-bit），困惑度增加 0.121。"
    v2 = verify("量化有什么缺点？", EVIDENCE, bad)
    assert v2["pass"] is False, "unsourced numbers must fail"
    assert set(v2["invented_numbers"]) == {"8", "0.121"}, v2

    assert digit_claims("由四个主要部分组成") == set(), "prose integers are not claims"
    assert digit_claims("如 8-bit") == {"8"}
    assert digit_claims("速度提升 30%") == {"30%"}
    ok("verify: unit/percentage claims caught, prose integers not")


def test_uint8_is_not_support():
    """`UINT8` in a tensor-type list must not back an 8-bit claim."""
    hay = "张量类型如 `UINT8`、`INT32`、`FLOAT32`"
    assert unsourced_claims("量化转成 8-bit 整数。", hay) == ["8"], \
        "letters glued to a digit are not a match for it"
    # ... while evidence spelled 400MB must support an answer saying 400 MB
    assert unsourced_claims("文件约 400 MB。", "the file is 400MB") == []
    # and 12.5 must not pass because of an unrelated 112.55
    assert unsourced_claims("延迟 12.5ms。", "总耗时 112.55ms") == ["12.5"]
    ok("verify: token-boundary support, unit span folding")


def test_two_char_terms_count_as_topic():
    anch = relevance_terms("量化有什么缺点？")
    assert "量化" in anch and "缺点" in anch, anch
    v = verify("量化有什么缺点？", EVIDENCE,
               "量化会减少存储体积，但可能损失精度。")
    assert v["on_topic"] is True, "a correct paraphrase must not read as off-topic"
    ok("verify: 2-char Chinese content terms count for relevance")


def test_decline_family_and_direct_gate():
    assert verify("Q4_K_M 是什么？", [], "我目前没有关于这一术语的具体信息。")[
        "pass"] is True, "an honest decline must pass"
    assert verify("Q4_K_M 是什么？", [],
                  "Q4_K_M 是衡量模型在 Q4 期间性能的指标。")["pass"] is False, \
        "fabricating with no evidence must fail"
    d = verify("给我讲个笑话", [], "当然可以，有个程序员笑话。", searched=False)
    assert d["pass"] is True and d["reason"] == "direct", d
    dn = verify("给我讲个笑话", [], "延迟大约是 12.5ms，够快了。", searched=False)
    assert dn["pass"] is False and dn["reason"] == "direct-unsourced-numbers", dn
    ok("verify: declines accepted, direct turns still gated on numbers")


def test_hits_are_deterministic():
    v = verify("Q4_K_M 是什么？", EVIDENCE,
               "Q4_K_M 是 4 bit 的 K-quant，困惑度 +0.1754。")
    assert v["hits"] == sorted(v["hits"]), v["hits"]
    ok("verify: hits sample sorted (set order is hash-randomized)")


# -- deepwiki retry ---------------------------------------------------------

LIMIT = "Error processing question: Client error '429 Too Many Requests' for url x"
PERMANENT = "Error processing question: repo not found"
ANSWER = "Q4_K_M is a 4-bit K-quant block format."


def fake(bodies):
    state = {"calls": 0}

    def call():
        body = bodies[min(state["calls"], len(bodies) - 1)]
        state["calls"] += 1
        return body
    return call, state


def test_rate_limit_backoff():
    call, st = fake([LIMIT] * 3)
    sleeps = []
    out = dw.deepwiki_ask(None, "r", "q", tries=3, sleeper=sleeps.append, call=call)
    assert st["calls"] == 3 and sleeps == [2.0, 4.0], (st, sleeps)
    assert out.startswith("__ERR__ deepwiki ratelimited"), out
    ok("deepwiki: rate limit retried with deterministic backoff")

    call2, st2 = fake([LIMIT, ANSWER])
    s2 = []
    out2 = dw.deepwiki_ask(None, "r", "q", tries=3, sleeper=s2.append, call=call2)
    assert out2.startswith("【DeepWiki:r】") and s2 == [2.0], (out2, s2)
    ok("deepwiki: limit then success returns evidence")

    call3, st3 = fake([PERMANENT] * 3)
    out3 = dw.deepwiki_ask(None, "r", "q", tries=3, sleeper=lambda s: None,
                           call=call3)
    assert st3["calls"] == 1 and out3.startswith("__ERR__ deepwiki error"), \
        (st3, out3)
    ok("deepwiki: permanent error is not retried")

    assert dw.looks_like_error(LIMIT) and not dw.looks_like_error(ANSWER)
    assert not dw.looks_like_error("量化会降低模型体积。"), "Chinese prose must not trip the gate"
    ok("deepwiki: error bodies detected, answers not")


# -- loop wiring ------------------------------------------------------------

def test_loop_uses_new_gate():
    orig_retrieve = loop.retrieve
    try:
        loop.retrieve = lambda q, **kw: (EVIDENCE, ["stub:1"])
        seen = {}

        def fake_summarize(question, evidence, searched):
            seen["args"] = (question, len(evidence), searched)
            # phrased close to the evidence on purpose: the overlap floor is a
            # known limit carried over from lyco-model (a correct paraphrase of
            # long evidence can still read as low-overlap), so this test checks
            # wiring, not that floor.
            return {"response": "Q4_K_M 是 4 bit 的 K-quant 超级块格式，"
                                "困惑度增加 +0.1754，文件约 400MB。",
                    "gen_ts": 90.0, "elapsed": 0.1, "rc": 0}

        r = core.answer("Q4_K_M 是什么？", summarize_fn=fake_summarize)
        assert r["routed_search"] is True and seen["args"][1] == 1
        assert r["verify"]["pass"] is True, r["verify"]
        assert r["retrieve_notes"] == ["stub:1"]
        direct = core.answer("给我讲个笑话", summarize_fn=lambda *a, **k: {
            "response": "为什么程序员喜欢黑暗模式？", "gen_ts": None,
            "elapsed": 0.1, "rc": 0})
        assert direct["routed_search"] is False and \
            direct["verify"]["reason"] == "direct"
        ok("loop: injected summarizer, routing and verify wired end to end")
    finally:
        loop.retrieve = orig_retrieve


if __name__ == "__main__":
    test_cue_routing()
    test_no_wikipedia_source()
    test_claims_must_be_sourced()
    test_uint8_is_not_support()
    test_two_char_terms_count_as_topic()
    test_decline_family_and_direct_gate()
    test_hits_are_deterministic()
    test_rate_limit_backoff()
    test_loop_uses_new_gate()
    print(f"\n{len(PASSED)} groups PASSED")
