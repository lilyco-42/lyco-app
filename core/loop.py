"""lyco OODA loop: one closed loop per dialogue turn."""
import time

from core.retrievers import http
from core.retrievers.deepwiki import deepwiki_ask
from core.retrievers.local import local_search
from core.retrievers.rss import rss_search
from core.router import needs_evidence, pick_repo, source_order
from core.summarizer import summarize
from core.verify import relevance_terms, verify


def retrieve(question, max_rounds=2, max_chars=1200):
    """OODA Observe/Orient: gather up to max_rounds sources (no early
    stop: a weak local hit must not block a better DeepWiki hit).

    Wikipedia is not among them -- see core/router.source_order."""
    client = http()
    evidence, notes = [], []
    repo = pick_repo(question)
    tried = 0
    for src in source_order(question):
        if tried >= max_rounds:
            break
        if src == "local":
            hits = local_search(question)
            notes.append(f"local:{len(hits)}")
            evidence += hits
            tried += 1
        elif src == "rss":
            hits, errs = rss_search(client, question)
            notes += errs if not hits else [f"rss:{len(hits)}"]
            evidence += hits
            tried += 1
        elif src == "deepwiki":
            if repo:
                d = deepwiki_ask(client, repo, question)
                if d and not d.startswith("__ERR__"):
                    evidence.append(d)
                    notes.append(f"deepwiki:{repo}")
                elif d:
                    notes.append(d[:80])
            else:
                notes.append("deepwiki:skip-no-repo")
            tried += 1
    client.close()
    # cap total evidence for the small model's context
    kept, total = [], 0
    for ev in evidence:
        if total >= max_chars:
            break
        kept.append(ev[:max_chars - total])
        total += len(kept[-1])
    return kept, notes


def answer(question, summarize_fn=None, topic="", prior_evidence=()):
    """One closed OODA loop per dialogue turn.

    `summarize_fn` is injectable so tests and any non-local backend can run
    the loop without llama-cli on the box (CI has no model, and AGENTS.md
    forbids building one here). `topic`/`prior_evidence` are what a caller with
    conversation memory passes in; they are optional for now."""
    t0 = time.time()
    summarize_fn = summarize_fn or summarize
    routed = needs_evidence(question, topic)
    if not routed:
        ev, notes = [], ["router:direct"]
    else:
        ev, notes = retrieve(question)
    s = summarize_fn(question, ev, searched=routed)
    v = verify(question, ev, s["response"], searched=routed,
               anchors=relevance_terms(question), prior_evidence=prior_evidence)
    return {"question": question, "routed_search": routed,
            "evidence": ev, "retrieve_notes": notes,
            "verify": v, "total_elapsed": round(time.time() - t0, 2), **s}
