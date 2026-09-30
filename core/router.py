"""Router: knowledge questions trigger search; chit-chat goes direct."""
import re

SEARCH_TRIGGERS = ["什么是", "是什么", "什么叫", "是啥", "啥是", "何为",
                   "为何", "为什么", "如何", "怎么",
                   "介绍", "含义", "意思", "关系", "区别", "是谁", "有哪些",
                   "最新", "多少", "何时"]

# repo-question -> DeepWiki repo mapping (extensible)
REPO_MAP = [("llama", "ggml-org/llama.cpp"),
            ("gguf", "ggml-org/llama.cpp"),
            ("量化", "ggml-org/llama.cpp"),
            ("qwen", "QwenLM/Qwen3"),
            ("transformer", "huggingface/transformers")]


def need_search(question):
    return any(t in question for t in SEARCH_TRIGGERS)


def pick_repo(question):
    q = question.lower()
    for key, repo in REPO_MAP:
        if key.lower() in q:
            return repo
    return None


def source_order(question):
    if any(k in question for k in ("mpkg", "lilyco", "lyco", "记忆包")):
        return ["local", "deepwiki", "rss", "wiki"]
    if re.search(r"[Rr]ust|cargo|日报", question):
        return ["rss", "local", "deepwiki", "wiki"]
    return ["local", "deepwiki", "rss", "wiki"]
