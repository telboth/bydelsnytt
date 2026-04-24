"""OpenGraph-bilde-henter med persistent cache.

Henter `<meta property="og:image">` (eller twitter:image som fallback) for
hver unike artikkel-URL, cacher resultatet i images.json og fyller inn
image_url-feltet på stories.

Rate-limit: max N nye fetches per kjøring for å unngå å hamre opprinnelige
sider. URLer som tidligere ga None eller feilmelding cachesogså (med TTL).
"""
from __future__ import annotations

import html as _html
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

SKIP_SOURCES = {"events", "ruter-avvik", "ruter-sx", "reddit-oslo"}

MAX_NEW_FETCHES_PER_RUN = 60
FETCH_TIMEOUT = 4
REVALIDATE_AFTER_DAYS = 14

MAX_REVALIDATIONS_PER_RUN = 30
REVALIDATE_IMAGE_AFTER_DAYS = 21
HEAD_TIMEOUT = 3


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
            # HTML-entity-dekode (&amp; -> &, &#x2F; -> /, osv.) slik at URLen
            # blir et reelt HTTP-kall, ikke HTML-escapet string.
            img = _html.unescape(img)
            if img.startswith("//"):
                img = "https:" + img
            elif img.startswith("/"):
                img = urllib.parse.urljoin(base_url, img)
            if _PLACEHOLDER_RE.search(img):
                continue
            return img
    return None


def _quote_url(url: str) -> str:
    """Konverter unicode-tegn i path/query til percent-encoding.

    Merk: ; må beholdes i query-strings (valide parameter-separatorer og
    del av URLer som allerede inneholder encoded-tegn).
    """
    try:
        parts = urllib.parse.urlsplit(url)
        safe = urllib.parse.quote(parts.path, safe="/%:@")
        query = urllib.parse.quote(parts.query, safe="=&%:;,")
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


def _image_ok(img_url: str) -> bool:
    """HEAD-request — konservativ: marker KUN 404/410/403 som dødt.

    Timeout, rate-limit, 5xx, SSL-feil m.m. er ofte forbigående. Da beholder
    vi bildet. Vi vil heller ha et "midlertidig dødt" bilde i cachen (som
    onerror-handleren fjerner fra UI) enn å spole bort fungerende bilder.
    """
    decoded = _html.unescape(img_url)
    safe = _quote_url(decoded)
    try:
        req = urllib.request.Request(safe, headers={"User-Agent": UA}, method="HEAD")
        with urllib.request.urlopen(req, timeout=HEAD_TIMEOUT, context=SSL_CTX) as r:
            return 200 <= r.status < 400
    except urllib.error.HTTPError as e:
        # Bare permanent-borte-statuser blir markert dødt
        return e.code not in (404, 410, 403)
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError):
        # Nettverksfeil/timeout — antagelig forbigående
        return True


def _revalidate_age_days(entry: dict) -> float:
    ts = entry.get("last_checked_at") or entry.get("fetched_at", "")
    if not ts:
        return float("inf")
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    return (datetime.now(timezone.utc) - t).total_seconds() / 86400


def revalidate_cached_images(cache: dict, max_checks: int = MAX_REVALIDATIONS_PER_RUN) -> dict:
    """HEAD-sjekk de eldste cachede bildene. Nuller ut døde bilder."""
    candidates = [
        (url, entry) for url, entry in cache.items()
        if entry.get("image")
        and _revalidate_age_days(entry) > REVALIDATE_IMAGE_AFTER_DAYS
    ]
    candidates.sort(key=lambda kv: _revalidate_age_days(kv[1]), reverse=True)
    checked = 0
    dead = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for url, entry in candidates[:max_checks]:
        ok = _image_ok(entry["image"])
        if ok:
            entry["last_checked_at"] = now_iso
        else:
            entry["image"] = None
            entry["fetched_at"] = now_iso
            entry.pop("last_checked_at", None)
            dead += 1
        checked += 1
        time.sleep(0.05)
    return {"checked": checked, "dead": dead}


def prune_orphan_images(cache: dict, story_urls: set) -> int:
    """Fjern cache-entries som ikke lenger refereres av noen sak.

    Etter at cache.prune har fjernet gamle saker, vil images.json ha
    foreldreloese entries. Fjerner dem for aa begrense vekst.
    """
    orphans = [url for url in cache if url not in story_urls]
    for url in orphans:
        cache.pop(url, None)
    return len(orphans)


def enrich_images(stories, max_new=MAX_NEW_FETCHES_PER_RUN,
                  max_revalidations=MAX_REVALIDATIONS_PER_RUN):
    cache = load_cache()
    reval_stats = revalidate_cached_images(cache, max_checks=max_revalidations)
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
            time.sleep(0.05)
            entry = cache[url]

        if entry and entry.get("image"):
            s["image_url"] = _html.unescape(entry["image"])
            if not need_fetch:
                from_cache += 1

    save_cache(cache)
    return {
        "added": added,
        "from_cache": from_cache,
        "fetched_new": fetched_new,
        "failed": failed,
        "cache_size": len(cache),
        "revalidated": reval_stats["checked"],
        "revalidated_dead": reval_stats["dead"],
    }
