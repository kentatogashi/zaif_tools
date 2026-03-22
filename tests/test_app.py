import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from unittest.mock import patch
from urllib.error import URLError

from app import build_home_page, fetch_geoip


class MockHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_geoip_success():
    payload = {
        "success": True,
        "ip": "8.8.8.8",
        "continent": "North America",
        "continent_code": "NA",
        "country": "United States",
        "country_code": "US",
        "region": "California",
        "city": "Mountain View",
        "latitude": 37.386,
        "longitude": -122.0838,
        "postal": "94035",
        "timezone": {"id": "America/Los_Angeles", "utc": "-08:00"},
        "connection": {"asn": 15169, "org": "Google LLC", "isp": "Google LLC"},
    }

    with patch("app.urlopen", return_value=MockHTTPResponse(payload)):
        result = fetch_geoip("8.8.8.8")

    assert result["country_code"] == "US"
    assert result["connection"]["isp"] == "Google LLC"
    assert result["insights"]["country_flag"] == "🇺🇸"
    assert result["insights"]["ip_type"] == "public"
    assert result["insights"]["map_links"]["google_maps"].startswith("https://www.google.com/maps")


def test_geoip_invalid_ip():
    try:
        fetch_geoip("not-an-ip")
    except ValueError as exc:
        assert str(exc) == "Invalid IP address."
    else:
        raise AssertionError("ValueError was not raised")


def test_geoip_upstream_failure():
    with patch("app.urlopen", side_effect=URLError("boom")):
        try:
            fetch_geoip("1.1.1.1")
        except ConnectionError as exc:
            assert str(exc) == "Failed to reach the upstream GeoIP provider."
        else:
            raise AssertionError("ConnectionError was not raised")


def test_home_page_contains_form_and_health_hint():
    page = build_home_page()
    assert "GeoIP Explorer" in page
    assert "/health" in page
    assert "geoip-form" in page

