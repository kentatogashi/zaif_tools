import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from ipaddress import ip_address
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
from zoneinfo import ZoneInfo

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
GEOIP_PROVIDER_URL = "https://ipwho.is/{ip}"
TIMEOUT_SECONDS = 10


def build_json_response(status: int, payload: Dict[str, Any]) -> Tuple[int, bytes]:
    return status, json.dumps(payload, ensure_ascii=False).encode("utf-8")


def country_code_to_flag(code: Optional[str]) -> Optional[str]:
    if not code or len(code) != 2 or not code.isalpha():
        return None
    return "".join(chr(127397 + ord(char.upper())) for char in code)


def classify_ip(ip: str) -> str:
    candidate = ip_address(ip)
    if candidate.is_private:
        return "private"
    if candidate.is_loopback:
        return "loopback"
    if candidate.is_multicast:
        return "multicast"
    if candidate.is_reserved:
        return "reserved"
    return "public"


def build_insights(payload: Dict[str, Any]) -> Dict[str, Any]:
    timezone_id = payload.get("timezone")
    country_code = payload.get("country_code")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    local_time = None
    if timezone_id:
        try:
            local_time = datetime.now(ZoneInfo(timezone_id)).isoformat(timespec="seconds")
        except Exception:
            local_time = None

    map_links = {}
    if latitude is not None and longitude is not None:
        map_links = {
            "google_maps": f"https://www.google.com/maps?q={latitude},{longitude}",
            "openstreetmap": f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=10/{latitude}/{longitude}",
        }

    return {
        "ip_type": classify_ip(payload["ip"]),
        "country_flag": country_code_to_flag(country_code),
        "local_time": local_time,
        "queried_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "map_links": map_links,
    }


def fetch_geoip(ip: str) -> Dict[str, Any]:
    try:
        ip_address(ip)
    except ValueError as exc:
        raise ValueError("Invalid IP address.") from exc

    try:
        with urlopen(GEOIP_PROVIDER_URL.format(ip=ip), timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ConnectionError("Failed to reach the upstream GeoIP provider.") from exc

    if not payload.get("success", False):
        raise LookupError(payload.get("message", "GeoIP data not found."))

    normalized = {
        "ip": payload.get("ip"),
        "continent": payload.get("continent"),
        "continent_code": payload.get("continent_code"),
        "country": payload.get("country"),
        "country_code": payload.get("country_code"),
        "region": payload.get("region"),
        "city": payload.get("city"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone", {}).get("id"),
        "utc_offset": payload.get("timezone", {}).get("utc"),
        "postal_code": payload.get("postal"),
        "connection": {
            "asn": payload.get("connection", {}).get("asn"),
            "organization": payload.get("connection", {}).get("org"),
            "isp": payload.get("connection", {}).get("isp"),
        },
    }
    normalized["insights"] = build_insights(normalized)
    return normalized


def build_home_page() -> str:
    return """<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>GeoIP Explorer</title>
  <style>
    :root { color-scheme: dark; }
    body { font-family: system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    main { max-width: 880px; margin: 0 auto; padding: 48px 20px; }
    .card { background: #111827; border: 1px solid #334155; border-radius: 18px; padding: 24px; box-shadow: 0 12px 32px rgba(0,0,0,.25); }
    h1 { margin-top: 0; font-size: 2rem; }
    p { line-height: 1.6; color: #cbd5e1; }
    form { display: flex; gap: 12px; margin: 24px 0 16px; flex-wrap: wrap; }
    input { flex: 1; min-width: 240px; padding: 14px 16px; border-radius: 12px; border: 1px solid #475569; background: #020617; color: #fff; }
    button { padding: 14px 18px; border: 0; border-radius: 12px; background: linear-gradient(135deg,#38bdf8,#6366f1); color: white; font-weight: 700; cursor: pointer; }
    pre { margin: 0; padding: 18px; border-radius: 16px; background: #020617; overflow: auto; border: 1px solid #1e293b; }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0; }
    .chip { background: #1e293b; border: 1px solid #334155; color: #93c5fd; border-radius: 999px; padding: 6px 10px; font-size: .9rem; }
    .links a { color: #7dd3fc; margin-right: 12px; }
  </style>
</head>
<body>
  <main>
    <section class=\"card\">
      <h1>GeoIP Explorer</h1>
      <p>IP から位置情報を引くだけではなく、現地時刻・国旗・地図リンクまで返す、公開向けの GeoIP ウェブアプリです。</p>
      <div class=\"chips\">
        <span class=\"chip\">/geoip?ip=8.8.8.8</span>
        <span class=\"chip\">/geoip/1.1.1.1</span>
        <span class=\"chip\">/health</span>
      </div>
      <form id=\"geoip-form\">
        <input id=\"ip\" name=\"ip\" value=\"8.8.8.8\" placeholder=\"例: 8.8.8.8\" />
        <button type=\"submit\">Lookup</button>
      </form>
      <p class=\"links\">API JSON を直接使う: <a href=\"/geoip?ip=8.8.8.8\">sample endpoint</a></p>
      <pre id=\"result\">フォームから IP を検索すると、JSON がここに表示されます。</pre>
    </section>
  </main>
  <script>
    const form = document.getElementById('geoip-form');
    const result = document.getElementById('result');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const ip = document.getElementById('ip').value.trim();
      result.textContent = 'Loading...';
      try {
        const response = await fetch(`/geoip?ip=${encodeURIComponent(ip)}`);
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
      } catch (error) {
        result.textContent = JSON.stringify({ detail: 'Request failed.', error: String(error) }, null, 2);
      }
    });
  </script>
</body>
</html>"""


class GeoIPHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.respond_html(200, build_home_page())
            return

        if parsed.path == "/health":
            self.respond(200, {"status": "ok"})
            return

        ip = None
        if parsed.path == "/geoip":
            ip = parse_qs(parsed.query).get("ip", [None])[0]
        elif parsed.path.startswith("/geoip/"):
            ip = parsed.path.removeprefix("/geoip/") or None

        if ip is None:
            self.respond(404, {"detail": "Not found."})
            return

        try:
            payload = fetch_geoip(ip)
            self.respond(200, payload)
        except ValueError as exc:
            self.respond(400, {"detail": str(exc)})
        except LookupError as exc:
            self.respond(404, {"detail": str(exc)})
        except ConnectionError as exc:
            self.respond(502, {"detail": str(exc)})

    def respond(self, status: int, payload: Dict[str, Any]) -> None:
        _, body = build_json_response(status, payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = HOST, port: int = PORT) -> None:
    server = HTTPServer((host, port), GeoIPHandler)
    print(f"Serving GeoIP API on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
