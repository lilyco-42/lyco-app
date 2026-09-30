"""services.reviews — rank shops by aggregated review evidence.

Function interface only (services 层只暴露函数接口, 见 docs/ARCHITECTURE.md):
- rank_shops(pois, question=None, answer_fn=None) -> list[dict]
"""
from .reviews import DEFAULT_QUESTION, rank_shops

__all__ = ["rank_shops", "DEFAULT_QUESTION"]
