"""Amap (高德) Web Service v3 POI search: place/around + place/detail.

Design notes:
- API key comes ONLY from the ``AMAP_WEBSERVICE_KEY`` env var; never hardcoded.
- HTTP goes through the module-level ``_http_get`` callable (default
  ``httpx.get``) so tests can inject a fake client and run fully offline.
- Only documented Amap v3 fields are surfaced: name / address / location /
  distance / tel / rating / photos / cost.
- Any response with ``infocode != "10000"`` raises :class:`POIError`
  carrying the server's ``info`` message.

Endpoints (Amap Web Service v3, GET):
- https://restapi.amap.com/v3/place/around
- https://restapi.amap.com/v3/place/detail
"""
from __future__ import annotations

import os
from typing import Any, Callable

import httpx

AROUND_URL = "https://restapi.amap.com/v3/place/around"
DETAIL_URL = "https://restapi.amap.com/v3/place/detail"

SUCCESS_INFOCODE = "10000"

#: Injectable HTTP client (module-level so tests can swap it out).
_http_get: Callable[..., Any] = httpx.get

REQUEST_TIMEOUT_S = 10.0


class POIError(RuntimeError):
    """Raised when Amap reports an error (infocode != 10000) or the key is missing."""


def _key() -> str:
    """Read the Web Service key from env; fail loudly if absent."""
    key = os.environ.get("AMAP_WEBSERVICE_KEY", "")
    if not key:
        raise POIError("AMAP_WEBSERVICE_KEY env var is not set")
    return key


def _s(value: Any) -> str:
    """Normalize an Amap scalar field to str.

    Amap quirks: ``address`` / ``tel`` come back as ``[]`` (empty list) or
    ``None`` when absent; nested containers are flattened to "" here.
    """
    if value is None or isinstance(value, (list, dict)):
        return ""
    return str(value)


def _get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    """GET + parse + infocode gate shared by both endpoints."""
    resp = _http_get(url, params=params, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise POIError(f"unexpected amap payload from {url}: {data!r}")
    infocode = _s(data.get("infocode"))
    if infocode != SUCCESS_INFOCODE:
        raise POIError(
            f"amap error infocode={infocode!r} info={_s(data.get('info'))!r} url={url}"
        )
    return data


def nearby_search(
    lat: float,
    lng: float,
    radius_m: int = 1000,
    types: str | None = None,
    keywords: str | None = None,
) -> list[dict[str, str]]:
    """Search POIs around (lat, lng) within ``radius_m`` meters.

    Returns a list of dicts with keys: name / address / location / distance /
    tel. ``location`` is Amap's "lng,lat" string; ``distance`` is the meters
    string Amap returns for around searches. Empty result -> [].
    """
    params: dict[str, str] = {
        "key": _key(),
        "location": f"{lng:.6f},{lat:.6f}",
        "radius": str(int(radius_m)),
    }
    if types:
        params["types"] = types
    if keywords:
        params["keywords"] = keywords
    data = _get_json(AROUND_URL, params)
    pois = data.get("pois") or []
    return [
        {
            "name": _s(p.get("name")),
            "address": _s(p.get("address")),
            "location": _s(p.get("location")),
            "distance": _s(p.get("distance")),
            "tel": _s(p.get("tel")),
        }
        for p in pois
        if isinstance(p, dict)
    ]


def place_detail(poi_id: str) -> dict[str, Any]:
    """Fetch one POI's detail by its id (Amap place/detail, extensions=all).

    Returns a dict with keys: name / address / tel / rating / photos / cost.
    ``rating`` / ``cost`` are strings from ``biz_ext`` ("" when absent);
    ``photos`` is a list of {"title", "url"} dicts (empty when absent).
    Raises POIError when the id resolves to nothing.
    """
    data = _get_json(DETAIL_URL, {"key": _key(), "id": poi_id, "extensions": "all"})
    pois = data.get("pois") or []
    if not pois:
        raise POIError(f"amap place/detail returned no pois for id={poi_id!r}")
    poi = pois[0]
    biz_ext = poi.get("biz_ext")
    if not isinstance(biz_ext, dict):
        biz_ext = {}
    photos = [
        {"title": _s(ph.get("title")), "url": _s(ph.get("url"))}
        for ph in (poi.get("photos") or [])
        if isinstance(ph, dict)
    ]
    return {
        "name": _s(poi.get("name")),
        "address": _s(poi.get("address")),
        "tel": _s(poi.get("tel")),
        "rating": _s(biz_ext.get("rating")),
        "photos": photos,
        "cost": _s(biz_ext.get("cost")),
    }
