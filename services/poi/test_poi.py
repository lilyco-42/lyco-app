"""test_poi: offline tests for services.poi (fake HTTP client, no network).

Run:  python services/poi/test_poi.py
No real API call, no AMAP_WEBSERVICE_KEY needed: the HTTP layer
(amap._http_get) is replaced with a fake that replays canned Amap payloads.

Covers: nearby success / empty / error, detail success / error,
missing-key guard, and that requests carry the env-provided key only.
"""
from __future__ import annotations

import contextlib
import os
import sys
import traceback
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.poi import POIError, amap, nearby_search, place_detail  # noqa: E402

TEST_KEY = "test-key-injected-via-env"


class FakeResp:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, data: Any) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self._data


class FakeClient:
    """Replaces amap._http_get; records the call and replays canned data."""

    def __init__(self, data: Any) -> None:
        self.data = data
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, params: Any = None, timeout: Any = None) -> FakeResp:
        self.calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        return FakeResp(self.data)


@contextlib.contextmanager
def _offline(data: Any):
    """Swap in the fake client + a fake env key; restore both on exit."""
    old_key = os.environ.get("AMAP_WEBSERVICE_KEY")
    old_get = amap._http_get
    os.environ["AMAP_WEBSERVICE_KEY"] = TEST_KEY
    fake = FakeClient(data)
    amap._http_get = fake
    try:
        yield fake
    finally:
        amap._http_get = old_get
        if old_key is None:
            os.environ.pop("AMAP_WEBSERVICE_KEY", None)
        else:
            os.environ["AMAP_WEBSERVICE_KEY"] = old_key


# --- canned Amap v3 payloads (shape per lbs.amap.com docs) -------------------

AROUND_OK = {
    "status": "1", "info": "OK", "infocode": "10000", "count": "2",
    "pois": [
        {"id": "B0FFH12345", "name": "星美理发店",
         "address": "北京市朝阳区幸福路1号",
         "location": "116.481028,39.989643",
         "tel": "010-66668888", "distance": "121"},
        {"id": "B0FFH67890", "name": "洗剪吹快剪",
         "address": [],              # Amap quirk: [] when absent
         "location": "116.485288,39.988312",
         "tel": [],                  # Amap quirk
         "distance": "453"},
    ],
}

AROUND_EMPTY = {
    "status": "1", "info": "OK", "infocode": "10000",
    "count": "0", "pois": [],
}

AMAP_ERROR = {"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"}

DETAIL_OK = {
    "status": "1", "info": "OK", "infocode": "10000",
    "pois": [{
        "id": "B0FFH12345", "name": "星美理发店",
        "address": "北京市朝阳区幸福路1号",
        "location": "116.481028,39.989643",
        "tel": "010-66668888",
        "photos": [{"title": "门脸", "url": "https://aos-comment.amap.com/photo1.jpg"},
                   {"title": "店内", "url": "https://aos-comment.amap.com/photo2.jpg"}],
        "biz_ext": {"rating": "4.5", "cost": "68"},
    }],
}

DETAIL_NO_EXTRAS = {
    "status": "1", "info": "OK", "infocode": "10000",
    "pois": [{
        "id": "B0FFH67890", "name": "洗剪吹快剪",
        "address": [], "tel": [],
        # no photos / no biz_ext in payload
    }],
}


# --- tests ---------------------------------------------------------------

def test_nearby_success():
    with _offline(AROUND_OK) as fake:
        res = nearby_search(39.989643, 116.481028, radius_m=1000,
                            types="060400")
    assert len(res) == 2, res
    assert res[0]["name"] == "星美理发店"
    assert res[0]["address"] == "北京市朝阳区幸福路1号"
    assert res[0]["location"] == "116.481028,39.989643"
    assert res[0]["distance"] == "121"
    assert res[0]["tel"] == "010-66668888"
    # Amap [] quirks normalized to ""
    assert res[1]["address"] == "", res[1]
    assert res[1]["tel"] == "", res[1]
    # request carried the env key, lng/lat order, omitted Nones
    sent = fake.calls[0]["params"]
    assert sent["key"] == TEST_KEY, sent
    assert sent["location"] == "116.481028,39.989643", sent
    assert sent["radius"] == "1000", sent
    assert sent["types"] == "060400", sent
    assert "keywords" not in sent, sent


def test_nearby_empty():
    with _offline(AROUND_EMPTY):
        assert nearby_search(39.9, 116.4) == []


def test_nearby_error():
    with _offline(AMAP_ERROR):
        try:
            nearby_search(39.9, 116.4)
        except POIError as e:
            assert "10001" in str(e) and "INVALID_USER_KEY" in str(e), e
        else:
            raise AssertionError("expected POIError")


def test_detail_success():
    with _offline(DETAIL_OK):
        d = place_detail("B0FFH12345")
    assert d["name"] == "星美理发店", d
    assert d["tel"] == "010-66668888", d
    assert d["rating"] == "4.5", d
    assert d["cost"] == "68", d
    assert d["photos"] == [
        {"title": "门脸", "url": "https://aos-comment.amap.com/photo1.jpg"},
        {"title": "店内", "url": "https://aos-comment.amap.com/photo2.jpg"},
    ], d


def test_detail_no_extras():
    with _offline(DETAIL_NO_EXTRAS):
        d = place_detail("B0FFH67890")
    assert d["rating"] == "" and d["cost"] == "" and d["photos"] == [], d


def test_detail_error():
    with _offline(AMAP_ERROR):
        try:
            place_detail("B0FFH12345")
        except POIError as e:
            assert "10001" in str(e), e
        else:
            raise AssertionError("expected POIError")


def test_no_key():
    old_key = os.environ.pop("AMAP_WEBSERVICE_KEY", None)
    old_get = amap._http_get
    fake = FakeClient(AROUND_OK)
    amap._http_get = fake
    try:
        nearby_search(39.9, 116.4)
    except POIError as e:
        assert "AMAP_WEBSERVICE_KEY" in str(e), e
    else:
        raise AssertionError("expected POIError")
    finally:
        amap._http_get = old_get
        if old_key is not None:
            os.environ["AMAP_WEBSERVICE_KEY"] = old_key
    assert fake.calls == [], "no HTTP without key"


def main():
    tests = [test_nearby_success, test_nearby_empty, test_nearby_error,
             test_detail_success, test_detail_no_extras, test_detail_error,
             test_no_key]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print("ALL PASSED")


if __name__ == "__main__":
    main()
