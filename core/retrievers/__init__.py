"""Shared retrieval helpers: keyword scoring + http client.

Retrieval stopwords guard against question-word false positives.
"""
import os
import re

import httpx

RETRIEVE_STOP = {"什么", "么是", "什么是", "是什么", "怎么", "为什么", "为什",
                 "如何", "哪些", "多少", "介绍", "含义", "意思", "关系",
                 "怎样", "何为", "是啥", "啥是", "什么用", "有什么", "干什么",
                 "用处", "作用", "这是什么", "那是什么", "它和", "和", "的"}

UA = {"User-Agent": "lyco-rag/0.1 (local RAG demo; contact: lyco42)"}


def tokens(question):
    toks = set()
    for w in re.findall(r"[A-Za-z0-9_+\-#]{2,}", question):
        toks.add(w.lower())
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", question):
        toks.add(run)
        for i in range(len(run) - 1):
            toks.add(run[i:i + 2])
    return toks


def score_text(toks, text):
    tl = text.lower()
    return sum(1 for t in toks
               if t not in RETRIEVE_STOP and (t in tl or t in text))


def is_anchor(t):
    if re.fullmatch(r"[A-Za-z0-9_+\-#]{2,}", t):
        return True
    return len(t) >= 3 and t not in RETRIEVE_STOP


def has_anchor(toks, text):
    tl = text.lower()
    return any(is_anchor(t) and (t in tl or t in text) for t in toks)


def http():
    # Use system proxy from env (do NOT strip it); sanitize NO_PROXY
    # (a bare ::1 entry crashes httpx's URL parser).
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ.pop("no_proxy", None)
    return httpx.Client(timeout=30)
