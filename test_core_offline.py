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


# -- cli contract (what the DSH plugin shells out to) -----------------------

def test_cli_json_contract():
    import io
    import json

    from core import cli

    orig = loop.answer
    try:
        loop.answer = lambda q, **kw: {
            "question": q, "response": "答案。", "evidence": EVIDENCE,
            "retrieve_notes": ["local:1"], "total_elapsed": 0.5,
            "rc": 0, "gen_ts": 90.0, "elapsed": 0.4, "routed_search": True,
            "verify": verify(q, EVIDENCE, "答案。")}
        buf = io.StringIO()
        code = cli.run(["什么是 GGUF？"], out=buf)
        d = json.loads(buf.getvalue())
        assert code == 0 and d["mode"] == "ask", (code, d)
        assert d["answer"] == "答案。" and d["routed_search"] is True
        assert "verify" in d and "elapsed_s" in d

        buf2 = io.StringIO()
        code2 = cli.run([], out=buf2)
        d2 = json.loads(buf2.getvalue())
        assert code2 == 2 and "error" in d2, (code2, d2)

        buf3 = io.StringIO()
        code3 = cli.run(["--shops", "理发"], out=buf3)
        d3 = json.loads(buf3.getvalue())
        assert code3 == 2 and "lat" in d3["error"], (code3, d3)
        ok("cli: one JSON object on stdout, exit 2 with {error} on bad input")
    finally:
        loop.answer = orig


# -- rss retriever ----------------------------------------------------------
#
# Fixture is built so the ranking assertion is sensitive to the title weight:
# item A and item B match the same 6 tokens but split them differently between
# title and description, so only `score_text(title) * 3` puts B first. Drop the
# weight and the two tie at 6, leaving A first -- the test then fails.

FEED = (
    "<rss><channel>"
    "<item><title>tokio 入门教程</title><link>https://rustcc.cn/i1</link>"
    "<description>&lt;p&gt;异步运行时 更新&lt;/p&gt;</description></item>"
    "<item><title>本周社区动态</title><link>https://rustcc.cn/i2</link>"
    "<description>闲聊灌水周报</description></item>"
    "<item><title>异步运行时 性能对比</title><link>https://rustcc.cn/i3</link>"
    "<description>tokio 讨论</description></item>"
    "</channel></rss>"
)

OTHER_FEED = (
    "<rss><channel><item><title>Tokio 2.0 发布</title>"
    "<link>https://rustcc.cn/new</link>"
    "<description>异步运行时 tokio 大版本</description></item>"
    "</channel></rss>"
)


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class _FeedClient:
    """Stand-in for httpx.Client: counts fetches so the cache branches are visible."""

    def __init__(self, text):
        self.text = text
        self.calls = 0

    def get(self, url, headers=None):
        self.calls += 1
        return _Resp(self.text)


class _NoNetwork:
    def get(self, url, headers=None):
        raise AssertionError("fresh cache must be read instead of the network")


def test_rss_retriever():
    import shutil
    import tempfile
    import time as _time
    from core.retrievers import rss as rss_mod

    tmp = tempfile.mkdtemp()
    cache = os.path.join(tmp, "rustcc_rss.xml")
    saved = rss_mod.RSS_CACHE
    try:
        rss_mod.RSS_CACHE = cache

        c = _FeedClient(FEED)
        ev, notes = rss_mod.rss_search(c, "tokio 异步运行时")
        assert c.calls == 1 and os.path.exists(cache), "first call must fetch and cache"
        assert notes == [], notes
        assert len(ev) == 2, f"topn=2, and 本周社区动态 must be filtered out: {ev}"
        assert "性能对比" in ev[0], f"title must outweigh description: {ev}"
        assert "入门教程" in ev[1], ev
        assert all("【RustCC:" in e and "来源:https://rustcc.cn/" in e for e in ev), ev
        assert "<p>" not in ev[1] and "&lt;" not in ev[1], f"html must be stripped: {ev[1]}"

        ev1, _ = rss_mod.rss_search(_NoNetwork(), "tokio 异步运行时", topn=1)
        assert len(ev1) == 1 and "性能对比" in ev1[0], ev1

        stale = _time.time() - rss_mod.RSS_TTL - 10
        os.utime(cache, (stale, stale))
        c2 = _FeedClient(OTHER_FEED)
        ev2, _ = rss_mod.rss_search(c2, "tokio 异步运行时")
        assert c2.calls == 1, "expired cache must refetch"
        assert len(ev2) == 1 and "Tokio 2.0" in ev2[0], ev2

        rss_mod.RSS_CACHE = os.path.join(tmp, "missing", "none.xml")

        class _Dead:
            def get(self, url, headers=None):
                raise RuntimeError("connection refused")

        ev3, notes3 = rss_mod.rss_search(_Dead(), "tokio")
        assert ev3 == [], ev3
        assert len(notes3) == 1 and notes3[0].startswith("rss-err:"), notes3
        assert "connection refused" in notes3[0], notes3

        ok("rss: cache write/read/TTL, title weighting, html strip, anchor filter, error note")
    finally:
        rss_mod.RSS_CACHE = saved
        shutil.rmtree(tmp, ignore_errors=True)


# -- summarizer: argv, prompt branches and echo parsing ----------------------

class _Proc:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_summarizer_offline():
    import importlib
    from core import summarizer as sm

    saved_run, saved_cli, saved_model = sm.subprocess.run, sm.LLAMA_CLI, sm.CHAT_MODEL
    seen = {}
    fake = {"stdout": b"", "stderr": b"", "rc": 0}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        seen["kw"] = kw
        return _Proc(stdout=fake["stdout"], stderr=fake["stderr"],
                     returncode=fake["rc"])

    try:
        sm.subprocess.run = fake_run
        sm.LLAMA_CLI, sm.CHAT_MODEL = "/bin/llama-cli", "/models/q4.gguf"

        sm.summarize("Q4_K_M 是什么？", ["资料甲", "资料乙"], True)
        argv = seen["argv"]
        assert argv[0] == "/bin/llama-cli" and argv[2] == "/models/q4.gguf", argv
        assert argv[argv.index("-n") + 1] == "256", argv
        assert "--single-turn" in argv and "--no-display-prompt" in argv, argv
        assert seen["kw"]["capture_output"] is True and seen["kw"]["timeout"] == 180
        prompt = argv[argv.index("-p") + 1]
        assert "【检索到的资料】\n资料甲\n资料乙" in prompt, prompt
        assert "只根据上述资料回答" in prompt and "就说不知道" in prompt, prompt

        sm.summarize("量化是什么？", [], True)
        pr2 = seen["argv"][seen["argv"].index("-p") + 1]
        assert "没有检索到相关资料" in pr2 and "【检索到的资料】" not in pr2, pr2

        sm.summarize("讲个笑话", [], False)
        pr3 = seen["argv"][seen["argv"].index("-p") + 1]
        assert pr3 == "讲个笑话", pr3

        pr = "PROMPT-TEXT"
        fake["stdout"] = ("some banner\n> " + pr + "\n真正的回答内容\n"
                          "[Prompt: blah blah\nExiting...\n").encode("utf-8")
        res = sm.summarize(pr, [], False)
        assert res["response"] == "真正的回答内容", res
        assert res["rc"] == 0 and res["gen_ts"] is None, res

        fake["stdout"] = ("Generation: 24.9 t/s\n" + pr + "...(truncated)\n"
                          "截断后的回答\nExiting...").encode("utf-8")
        res2 = sm.summarize(pr, [], False)
        assert res2["response"] == "截断后的回答", res2
        assert res2["gen_ts"] == 24.9, res2

        fake["stdout"] = "中文 gbk 回显".encode("gbk")
        fake["rc"] = 3
        res3 = sm.summarize("x", [], False)
        assert "中文 gbk 回显" in res3["response"], res3
        assert res3["rc"] == 3, res3

        assert sm.dec(b"") == "" and sm.dec(None) == ""

        os.environ["LYCO_LLAMA_CLI"] = "/opt/other-cli"
        os.environ["LYCO_CHAT_MODEL"] = "/opt/other.gguf"
        importlib.reload(sm)
        assert sm.LLAMA_CLI == "/opt/other-cli" and sm.CHAT_MODEL == "/opt/other.gguf"
        ok("summarizer: argv flags, three prompt branches, echo/truncation parse, "
           "gbk decode, env override")
    finally:
        sm.subprocess.run = saved_run
        for k in ("LYCO_LLAMA_CLI", "LYCO_CHAT_MODEL"):
            os.environ.pop(k, None)
        importlib.reload(sm)
        assert sm.LLAMA_CLI == saved_cli and sm.CHAT_MODEL == saved_model


if __name__ == "__main__":
    test_cue_routing()
    test_no_wikipedia_source()
    test_claims_must_be_sourced()
    test_uint8_is_not_support()
    test_two_char_terms_count_as_topic()
    test_decline_family_and_direct_gate()
    test_hits_are_deterministic()
    test_rate_limit_backoff()
    test_rss_retriever()
    test_summarizer_offline()
    test_loop_uses_new_gate()
    test_cli_json_contract()
    print(f"\n{len(PASSED)} groups PASSED")
