"""Router: which turns need a retrieval round, and from where.

Two fixes carried over from lyco-model's measured run (see
lyco-model/DEMO_100rounds.md section 11-12):

  - a factual ask is not always phrased with 什么/为什么. "量化有什么缺点？" or
    "它会让模型跑得更快吗？" used to go direct, and direct turns were then
    rubber-stamped by the verifier. Cues and anaphora now force a search.
  - Wikipedia is out of the source rotation: from this egress every Wikimedia
    endpoint answers 403 through the proxy and times out without it
    (lyco-model/results/source_probe.json, 7 variants tried).
"""
import re

SEARCH_TRIGGERS = ["什么是", "是什么", "什么叫", "是啥", "啥是", "何为",
                   "为何", "为什么", "如何", "怎么",
                   "介绍", "含义", "意思", "关系", "区别", "是谁", "有哪些",
                   "最新", "多少", "何时"]

# Prediction / evaluation asks: no 什么 cue, but they still need evidence.
PREDICTION_CUES = ["会不会", "能不能", "是不是", "有没有", "影响", "导致",
                   "需要", "支持", "适合", "缺点", "优点", "可靠", "安全", "准确"]

# Referents. Only meaningful once a conversation has a topic to point at;
# kept narrower than the retrieval-rewrite markers so "然后给我讲个笑话"
# stays chit-chat instead of being dragged into a search.
REFERENTIAL = ["它", "他", "她", "它们", "其中", "这个", "那个", "这些", "那些",
               "这样", "那样", "刚才", "前面", "上面"]

# repo-question -> DeepWiki repo mapping (extensible)
REPO_MAP = [("llama", "ggml-org/llama.cpp"),
            ("gguf", "ggml-org/llama.cpp"),
            ("量化", "ggml-org/llama.cpp"),
            ("qwen", "QwenLM/Qwen3"),
            ("transformer", "huggingface/transformers")]


def need_search(question):
    return any(t in question for t in SEARCH_TRIGGERS)


def needs_evidence(question, topic=""):
    """Route to search when the turn makes a factual ask.

    `topic` is the last knowledge question in this conversation ('' when there
    is none); a referent is only resolvable against it."""
    if need_search(question) or any(c in question for c in PREDICTION_CUES):
        return True
    if not topic:
        return False
    return "吗" in question or any(r in question for r in REFERENTIAL)


def pick_repo(question):
    q = question.lower()
    for key, repo in REPO_MAP:
        if key.lower() in q:
            return repo
    return None


def source_order(question):
    if any(k in question for k in ("mpkg", "lilyco", "lyco", "记忆包")):
        return ["local", "deepwiki", "rss"]
    if re.search(r"[Rr]ust|cargo|日报", question):
        return ["rss", "local", "deepwiki"]
    return ["local", "deepwiki", "rss"]
