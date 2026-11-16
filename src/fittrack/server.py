"""Opt-in private server reader. No service addresses or credentials are bundled."""
from datetime import date
import gzip
import http.client
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from .ingest import ingest

CONFIG = {
    "training": ("FITTRACK_TRAINING_API_URL", "FITTRACK_TRAINING_TOKEN"),
    "body": ("FITTRACK_BODY_API_URL", "FITTRACK_BODY_TOKEN"),
}
MAX_BYTES = 8 * 1024 * 1024

class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("API redirect rejected")

def configuration(category):
    url_env, token_env = CONFIG[category]
    url, token = os.environ.get(url_env, "").strip(), os.environ.get(token_env, "").strip()
    if not url:
        raise ValueError(f"fill {url_env} with your own private server endpoint")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"{url_env} must be an HTTP(S) URL without embedded credentials or fragment")
    if not token:
        raise ValueError(f"fill {token_env} with your own server credential")
    if any(ord(c)<33 or ord(c)>126 for c in token):
        raise ValueError(f"{token_env} must not contain whitespace or non-ASCII header characters")
    return url, token

def request(category, query):
    url, token = configuration(category)
    req = urllib.request.Request(url, data=json.dumps(query).encode(), method="POST", headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json",
        "Accept-Encoding": "gzip", "User-Agent": "FitTrack/0.1-read-only",
    })
    try:
        with urllib.request.build_opener(RejectRedirects()).open(req, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("API response too large")
        if raw.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
                raw = compressed.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("decompressed API response too large")
        value = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Private server HTTP {exc.code}; response details omitted") from None
    except (OSError, UnicodeError, json.JSONDecodeError, http.client.HTTPException):
        raise ValueError("Private server request/decode failed; endpoint and response details omitted") from None
    if not isinstance(value, dict) or value.get("complete") is not True or value.get("truncated"):
        raise ValueError("server must return a complete response using the documented contract")
    return value

def sync(db, day):
    date.fromisoformat(day)
    # Validate all blank fields before sending either request.
    for category in CONFIG:
        configuration(category)
    training = request("training", {"date": day})
    body = request("body", {"date": day})
    sessions, readings = training.get("sessions"), body.get("body")
    if not isinstance(sessions, list) or not isinstance(readings, list):
        raise ValueError("server response needs a sessions list and a body list")
    if any(s.get("day") != day for s in sessions) or any(b.get("day") != day for b in readings):
        raise ValueError("server response date mismatch")
    return ingest(db, {"sessions": sessions, "body": readings}, "server")
