"""OpenGraph-bilde-henter med persistent cache.

Henter `<meta property="og:image">` (eller twitter:image som fallback) for
hver unike artikkel-URL, cacher resultatet i images.json og fyller inn
image_url-feltet på stories.

Rate-limit: max N nye fetches per kjøring for å unngå å hamre opprinnelige
sider. URLer som tidligere ga None eller feilmelding cachesogså (med TTL).
"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CACHE_PATH = Path(__file__).resolve().parent.parent / "images.json"
UA = "BydelsnyttOsloBot/0.1 (+https://telboth.github.io/bydelsnytt)"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# Kilder som ikke har artikkel-URL med og:image (events, t-baneavvik, reddit)
SKIP_SOURCES = {"events", "ruter-avvik", "ruter-sx", "reddit-oslo"}

MAX_NEW_FETCHES_PER_RUN = 60
FETCH_TIMEOUT = 4  # sekunder
REVALIDATE_AFTER_DAYS = 14


OG_RE = re.compile(
    r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
OG_RE_REVERSE = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
    re.I,
)
TWITTER_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[images] kunne ikke lese {CACHE_PATH.name}: {e}")
        return {}


def save_cache(cache: dict) -> None:
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


# Kjente placeholder-URLer som enkelte CMS-er returnerer som og:image uten
# at bildet faktisk finnes (il-try.no peker ofte mot /images/teaser uten filnavn).
_PLACEHOLDER_RE = re.compile(
    r'(/images/teaser/?$|/placeholder\.?(png|jpg|jpeg)?$|/default-og\.?(png|jpg|jpeg)?$)',
    re.I,
)


def _extract_og_image(html: str, base_url: str) -> Optional[str]:
    for pat in (OG_RE, OG_RE_REVERSE, TWITTER_RE):
        m = pat.search(html)
        if m:
            img = m.group(1).strip()
            if not img:
                continue
            if img.startswith("//"):
                img = "https:" + img
            elif img.startswith("/"):
                img = urllib.parse.urljoin(base_url, img)
            if _PLACEHOLDER_RE.search(img):
                continue  # hopp over kjente placeholders
            return img
    return None


def _quote_url(url: str) -> str:
    """Konverter unicode-tegn i path/query til percent-encoding."""
    try:
        parts = urllib.parse.urlsplit(url)
        safe = urllib.parse.quote(parts.path, safe="/%:@")
        query = urllib.parse.quote(parts.query, safe="=&%:")
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, safe, query, parts.fragment)
        )
    except Exception:
        return url


def _fetch_page(url: str) -> Optional[str]:
    safe_url = _quote_url(url)
    try:
        req = urllib.request.Request(safe_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT, context=SSL_CTX) as r:
            raw = r.read(200_000)
            return raw.decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            OSError, UnicodeError, ValueError):
        return None


def _cache_stale(entry: dict) -> bool:
    if entry.get("image"):
        return False
    ts = entry.get("fetched_at", "")
    if not ts:
        return True
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    age_days = (datetime.now(timezone.utc) - t).total_seconds() / 86400
    return age_days > REVALIDATE_AFTER_DAYS


def enrich_images(stories, max_new=MAX_NEW_FETCHES_PER_RUN):
    cache = load_cache()
    added = 0
    from_cache = 0
    fetched_new = 0
    failed = 0

    for s in stories:
        if s.get("image_url"):
            continue
        sid = s.get("source_id", "")
        if sid in SKIP_SOURCES:
            continue
        url = (s.get("url") or "").strip()
        if not url:
            continue

        entry = cache.get(url)
        need_fetch = entry is None or _cache_stale(entry)
        if need_fetch and fetched_new < max_new:
            html = _fetch_page(url)
            img = _extract_og_image(html, url) if html else None
            cache[url] = {
                "image": img,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            fetched_new += 1
            if img:
                added += 1
            else:
                failed += 1
          