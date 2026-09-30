"""services.poi — Amap POI lookup (place/around + place/detail).

Function interface only (services 层只暴露函数接口, 见 docs/ARCHITECTURE.md):
- nearby_search(lat, lng, radius_m, types, keywords) -> list[dict]
- place_detail(poi_id) -> dict
"""
from .amap import POIError, nearby_search, place_detail

__all__ = ["nearby_search", "place_detail", "POIError"]
