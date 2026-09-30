"""Local kb retriever (gh-cloned repos): keyword score over md/toml/txt."""
import os

from core.retrievers import has_anchor, score_text, tokens

KB_DIR = r"D:\gal\AliceInCradle\kb"


def local_search(question, topn=2):
    """Local kb (gh-cloned repos): keyword score over md/toml/txt."""
    toks = tokens(question)
    hits = []
    if not os.path.isdir(KB_DIR):
        return []
    for root, dirs, files in os.walk(KB_DIR):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "target", "node_modules",
                                ".obsidian")]
        for fn in files:
            if not fn.lower().endswith((".md", ".markdown", ".txt",
                                        ".toml")):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except Exception:
                continue
            s = score_text(toks, text)
            if s >= 2 and has_anchor(toks, text):
                idx = max([text.find(t) for t in toks if t in text],
                          default=0)
                start = max(0, idx - 100)
                rel = os.path.relpath(p, KB_DIR)
                hits.append((s, f"【本地库:{rel}】{text[start:start + 500]}"))
    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:topn]]
