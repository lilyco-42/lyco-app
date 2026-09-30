"""lyco core package: router -> retrieve -> summarize -> verify.

Ported from lyco-model/rag_loop.py, and kept in step with the fixes measured
there (see lyco-model/DEMO_100rounds.md sections 10-12):

  - Wikipedia is dropped as a source (every Wikimedia endpoint 403s from this
    egress; lyco-model/results/source_probe.json)
  - the verifier checks claims, not just overlap: decimals, percentages,
    3+ digit numbers and any number glued to a unit must exist in the evidence
    as a token
  - DeepWiki rate limits get exponential backoff; error text inside an HTTP
    200 is never accepted as evidence
  - a factual ask is routed even without a 什么/为什么 phrase

Retrieval sources (no self-build, all adopted):
  1. Local kb (D:/gal/AliceInCradle/kb, gh-cloned repos)
  2. RustCC RSS (rust news)
  3. DeepWiki official MCP https://mcp.deepwiki.com/mcp (repo knowledge)
Summarizer: local chat model, backend injectable via answer(summarize_fn=...)
so tests and CI run with no model on the box.
Loop cap: max 2 retrieval rounds (lyco OODA rule), evidence cap 1200 chars.
"""
from core.loop import answer, retrieve
from core.router import need_search, needs_evidence, pick_repo, source_order
from core.summarizer import summarize
from core.verify import relevance_terms, verify

__all__ = ["answer", "retrieve", "need_search", "needs_evidence",
           "pick_repo", "source_order", "summarize", "verify",
           "relevance_terms"]
