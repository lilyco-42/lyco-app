"""lyco core package: router -> retrieve -> summarize -> verify.

Extracted verbatim from lyco-model/rag_loop.py (behavior-preserving).

Retrieval sources (no self-build, all adopted):
  1. Local kb (D:/gal/AliceInCradle/kb, gh-cloned repos)
  2. RustCC RSS (rust news)
  3. DeepWiki official MCP https://mcp.deepwiki.com/mcp (repo knowledge)
  4. Wikipedia zh API (encyclopedia facts, on-demand)
Summarizer: local chat model via llama-cli.
Loop cap: max 2 retrieval rounds (lyco OODA rule), evidence cap 1200 chars.
"""
from core.loop import answer, retrieve
from core.router import need_search, pick_repo, source_order
from core.summarizer import summarize
from core.verify import verify

__all__ = ["answer", "retrieve", "need_search", "pick_repo",
           "source_order", "summarize", "verify"]
