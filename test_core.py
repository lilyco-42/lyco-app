"""test_core: 2-question smoke test for the lyco core RAG loop.

Q1 "mpkg 记忆包..." must route to search and answer from the local kb.
Q2 "给我讲一个笑话" must route direct (no search, no evidence).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import answer, need_search


def main():
    ok = True

    # Q1: mpkg local question -> routed search, answered from kb
    q1 = "mpkg 记忆包是什么？有什么用？"
    assert need_search(q1), "router must trigger search for Q1"
    r1 = answer(q1)
    print(f"[Q1] search={r1['routed_search']} "
          f"ev={len(r1['evidence'])} notes={r1['retrieve_notes']} "
          f"verify={r1['verify']} el={r1['total_elapsed']}s", flush=True)
    print(f"[Q1] response: {r1['response'][:120]}", flush=True)
    assert r1["routed_search"] is True, "Q1 must be routed to search"
    assert r1["evidence"], "Q1 must gather evidence"
    kb_hits = [e for e in r1["evidence"] if e.startswith("【本地库:")]
    assert kb_hits, "Q1 evidence must come from the local kb"
    assert any("mpkg" in e.lower() for e in r1["evidence"]), \
        "Q1 evidence must mention mpkg"
    assert r1["rc"] == 0, "summarizer must exit cleanly for Q1"
    assert r1["verify"]["pass"], "Q1 verify must pass"
    ok &= True

    # Q2: joke -> routed direct, no search, no evidence
    q2 = "给我讲一个笑话"
    assert not need_search(q2), "router must NOT trigger search for Q2"
    r2 = answer(q2)
    print(f"[Q2] search={r2['routed_search']} "
          f"ev={len(r2['evidence'])} notes={r2['retrieve_notes']} "
          f"verify={r2['verify']} el={r2['total_elapsed']}s", flush=True)
    print(f"[Q2] response: {r2['response'][:120]}", flush=True)
    assert r2["routed_search"] is False, "Q2 must be routed direct"
    assert r2["evidence"] == [], "Q2 must have no evidence"
    assert r2["retrieve_notes"] == ["router:direct"]
    assert r2["verify"] == {"pass": True, "reason": "direct"}
    assert r2["response"].strip(), "Q2 must get a response from the model"
    assert r2["rc"] == 0, "summarizer must exit cleanly for Q2"

    print("ALL PASSED" if ok else "FAILED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
