"""test_reviews: offline tests for services.reviews (fake answer_fn).

Run:  python services/reviews/test_reviews.py
No pytest, no network, no llama-cli: answer_fn is injected with a fake
that replays canned core.loop.answer-shaped dicts and records queries.

Covers: ranked order (verified first, then evidence desc), empty pois,
failed verify sorts last, answer_fn receives a per-shop query containing
the shop name, nameless shops skipped, default Chinese question fallback.
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.reviews import DEFAULT_QUESTION, rank_shops  # noqa: E402


def canned_answer(evidence, verify_pass, reason, response):
    """core.loop.answer-shaped dict (only the keys rank_shops reads)."""
    return {"question": "", "routed_search": True,
            "evidence": evidence, "retrieve_notes": [],
            "verify": {"pass": verify_pass, "reason": reason},
            "total_elapsed": 0.0, "rc": 0, "response": response}


class FakeAnswer:
    """Replaces core.loop.answer; records queries, replays canned dicts."""

    def __init__(self, answers: list[dict]) -> None:
        self.answers = answers  # replayed in call order
        self.queries: list[str] = []

    def __call__(self, question: str) -> Any:
        self.queries.append(question)
        return self.answers.pop(0)


POIS = [
    {"id": "B0FFH12345", "name": "星美理发店",
     "address": "北京市朝阳区幸福路1号",
     "location": "116.481028,39.989643"},
    {"id": "B0FFH67890", "name": "洗剪吹快剪",
     "address": [],              # Amap quirk: [] when absent
     "location": "116.485288,39.988312"},
]


def test_ranked_order():
    fake = FakeAnswer([
        canned_answer(["ev1", "ev2"], True, "overlap=3", "星美理发店评价很好。"),
        canned_answer(["ev1"], False, "overlap=1", "洗剪吹快剪评价一般。"),
    ])
    res = rank_shops(POIS, question="哪家理发店最好？", answer_fn=fake)
    assert len(res) == 2, res
    # more evidence + verified -> first
    assert res[0]["name"] == "星美理发店", res
    assert res[1]["name"] == "洗剪吹快剪", res
    assert res[0]["summary"] == "星美理发店评价很好。", res
    assert res[0]["reason"] == "overlap=3", res
    assert res[1]["reason"] == "overlap=1", res
    assert set(res[0].keys()) == {"name", "address", "reason", "summary"}, res


def test_query_contains_shop_name():
    fake = FakeAnswer([
        canned_answer([], True, "direct", "无"),
        canned_answer([], True, "direct", "无"),
    ])
    rank_shops(POIS, answer_fn=fake)
    assert len(fake.queries) == 2, fake.queries
    # per-shop query carries the shop name and its address
    assert "星美理发店" in fake.queries[0], fake.queries
    assert "幸福路1号" in fake.queries[0], fake.queries
    assert "洗剪吹快剪" in fake.queries[1], fake.queries
    # Amap [] address must not leak into the query as "[]"
    assert "[]" not in fake.queries[1], fake.queries
    # None question falls back to the short Chinese default
    assert DEFAULT_QUESTION in fake.queries[0], fake.queries
    # a custom question flows into the per-shop query
    fake2 = FakeAnswer([canned_answer([], True, "direct", "x")])
    rank_shops(POIS[:1], question="哪家适合约会？", answer_fn=fake2)
    assert "哪家适合约会？" in fake2.queries[0], fake2.queries


def test_failed_verify_sorts_last():
    # shop A gets 5 evidence but verify fail; shop B gets 1 evidence verified
    fake = FakeAnswer([
        canned_answer([f"ev{i}" for i in range(5)], False, "overlap=0", "差评多。"),
        canned_answer(["ev0"], True, "overlap=2", "不错。"),
    ])
    res = rank_shops(POIS, answer_fn=fake)
    # verified-first beats raw evidence count
    assert res[0]["name"] == "洗剪吹快剪", res
    assert res[1]["name"] == "星美理发店", res


def test_empty_pois():
    fake = FakeAnswer([])
    assert rank_shops([], answer_fn=fake) == []
    assert fake.queries == [], fake.queries


def test_nameless_shop_skipped():
    pois = POIS + [{"id": "B3", "name": "", "address": "某路2号",
                    "location": "0,0"},
                   {"id": "B4", "address": "某路3号"}]
    fake = FakeAnswer([
        canned_answer(["e"], True, "overlap=2", "a"),
        canned_answer(["e", "e"], True, "overlap=2", "b"),
    ])
    res = rank_shops(pois, answer_fn=fake)
    assert len(res) == 2, res
    assert [r["name"] for r in res] == ["洗剪吹快剪", "星美理发店"], res
    assert len(fake.queries) == 2, fake.queries


def main():
    tests = [test_ranked_order, test_query_contains_shop_name,
             test_failed_verify_sorts_last, test_empty_pois,
             test_nameless_shop_skipped]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print("ALL PASSED")


if __name__ == "__main__":
    main()
