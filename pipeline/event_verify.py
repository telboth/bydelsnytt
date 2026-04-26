"""Auto-verifisering av kuraterte event-datoer i events.py.

Bakgrunn: events.py har hand-kuraterte datoer som er beste-estimat fra
typiske helg-monstre. Naar arrangoeren publiserer eksakt dato (typisk
endrer fra "23. august" til "8. august" som vi opplevde med Oslo Triathlon),
er det ingen ting som varsler oss.

Trinn:
  1) Hent side-teksten paa event-URL
  2) Regex-ekstrahering av datoer (raskt, gratis)
  3) Hvis regex ikke matcher (mismatch/no_dates), eskaler til Claude Haiku
     for aa tolke teksten naturlig — fanger 'Loerdag 8. mai', 'i pinsen' osv.
  4) Skriv rapport til event_verify.json

Vi gjoer IKKE auto-fix av events.py — rapport gir signal, mennesket bestemmer.

Skipper events der:
  - URL er Facebook/Wikipedia/Google Maps (ingen kanonisk dato paa siden)
  - Event_date er > 14 maaneder ute (arrangoer har ofte ikke publisert)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


REPORT_PATH = Path(__file__).resolve().parent.parent / "event_verify.json"
UA = "Mozilla/5.0 (bydelsnytt-bot; verify-events)"
TIMEOUT = 12

# Claude-fallback for uklare tilfeller
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 80
CLAUDE_TIMEOUT = 20
# Max antall Claude-call per kjoering (cost-cap)
CLAUDE_MAX_CALLS = 15

CLAUDE_SYSTEM_PROMPT = (
    "Du er en assistent som identifiserer dato for et arrangement i Oslo "
    "ut fra teksten paa arrangoerens hjemmeside. Svar KUN i formatet "
    "'YYYY-MM-DD' for datoen som mest sannsynlig er hovedarrangementet i "
    "2026 eller 2027. Hvis siden ikke nevner dato eller bare nevner gamle "
    "datoer, svar 'unknown'. Ingen forklaring, ingen ekstra tekst."
)

_NORSKE_MND = {
    "januar": "01", "februar": "02", "mars": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "desember": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "okt": "10", "nov": "11", "des": "12",
}

# URLer vi ikke kan/skal verifisere mot
SKIP_DOMAINS = (
    "facebook.com", "instagram.com", "google.com/maps",
    "wikipedia.org", "speiding.no/oslokrets",
    "no.wikipedia.org",
)


def _strip_html(html: str) -> str:
    """Fjern script/style + tags. Returner kun synlig tekst."""
    s = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL)
    s = re.sub(r"<style[^>]*>.*?</style>", " ", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_dates(text: str, current_year: int) -> list[date]:
    """Finn fremtidige datoer i tekst (norske formater).

    Stoetter:
      - 'dd. maaned' eller 'dd.mm' med eller uten aar
      - dd.mm.yyyy
      - yyyy-mm-dd

    Returnerer kun datoer >= i dag.
    """
    today = date.today()
    out: list[date] = []

    # 1. dd. <maaned> [yyyy]
    for m in re.finditer(
        r"\b(\d{1,2})[\.\s]+("
        r"januar|februar|mars|april|mai|juni|juli|august|"
        r"september|oktober|november|desember|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|okt|nov|des)"
        r"\.?\s*(\d{4})?",
        text, re.IGNORECASE,
    ):
        day = int(m.group(1))
        mon = _NORSKE_MND[m.group(2).lower()]
        year = int(m.group(3)) if m.group(3) else current_year
        if year < current_year:
            year = current_year + 1  # fremtidig
        try:
            d = date(year, int(mon), day)
            if d >= today:
                out.append(d)
        except ValueError:
            pass

    # 2. dd.mm.yyyy
    for m in re.finditer(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text):
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if d >= today:
                out.append(d)
        except ValueError:
            pass

    # 3. ISO yyyy-mm-dd
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d >= today:
                out.append(d)
        except ValueError:
            pass

    return sorted(set(out))


def _fetch(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            return raw.decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None


def _resolve_claude_key() -> str:
    """Hent ANTHROPIC_API_KEY fra env eller .anthropic_key-fil i repo-rot."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    key_file = Path(__file__).resolve().parent.parent / ".anthropic_key"
    if key_file.exists():
        try:
            return key_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return ""


def _ask_claude_for_date(api_key: str, title: str, expected: str,
                        page_text: str) -> Optional[str]:
    """Send tittel + sidetekst til Haiku, faa ISO-dato eller 'unknown' tilbake."""
    # Trim sidetekst til ~3000 tegn for kost-effektivitet (~750 input-tokens)
    excerpt = page_text[:3000]
    prompt = (
        f"Tittel paa arrangement: {title}\n"
        f"Var beste-estimat-dato (kan vaere feil): {expected}\n\n"
        f"Tekst fra arrangoerens hjemmeside:\n{excerpt}\n\n"
        "Hva er den faktiske datoen for hovedarrangementet i 2026 eller 2027? "
        "Svar bare med YYYY-MM-DD eller 'unknown'."
    )
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        req = urllib.request.Request(
            CLAUDE_API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=CLAUDE_TIMEOUT) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            OSError, json.JSONDecodeError) as e:
        print(f"  [verify] Claude error: {type(e).__name__}: {e}",
              file=sys.stderr)
        return None
    blocks = payload.get("content") or []
    for blk in blocks:
        if blk.get("type") == "text":
            text = (blk.get("text") or "").strip()
            # Trekk ut ISO-dato fra svaret (Haiku kan klone tilbake datoen
            # i en setning)
            m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
            if m:
                try:
                    d = date(int(m.group(1)), int(m.group(2)),
                              int(m.group(3)))
                    return d.isoformat()
                except ValueError:
                    return None
            return None
    return None


def _content_hash(text: str) -> str:
    h = hashlib.sha1(text[:5000].encode("utf-8")).hexdigest()
    return h[:16]


def _load_cache() -> dict:
    if not REPORT_PATH.exists():
        return {}
    try:
        prev = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        # Bygg dict id -> {hash, claude_suggested}
        cache = {}
        for item in prev.get("items", []):
            if item.get("claude_hash"):
                cache[item["id"]] = {
                    "hash": item["claude_hash"],
                    "suggested": item.get("claude_suggested"),
                }
        return cache
    except (OSError, json.JSONDecodeError):
        return {}


def _should_skip(url: str) -> bool:
    low = url.lower()
    return any(d in low for d in SKIP_DOMAINS)


def check_event(event: dict, claude_key: str = "",
                cache: Optional[dict] = None,
                budget: Optional[list] = None) -> dict:
    """Verifiser en enkelt event mot dens URL.

    Status: 'ok' / 'mismatch' / 'no_dates' / 'skipped' / 'fetch_failed'.
    Hvis claude_key er satt og budget tillater, brukes Claude som fallback
    for mismatch og no_dates.
    """
    expected = event.get("event_date") or ""
    url = event.get("url") or ""
    title = event.get("title") or ""
    base = {
        "id": event.get("id"), "title": title, "url": url,
        "expected": expected, "found": [], "status": "skipped",
        "note": "",
    }
    if not url or not expected:
        base["note"] = "mangler URL eller dato"
        return base
    if _should_skip(url):
        base["note"] = "URL er social/wiki/maps - ingen kanonisk dato"
        return base
    try:
        exp_d = date.fromisoformat(expected)
    except ValueError:
        base["status"] = "skipped"
        base["note"] = "ugyldig event_date i events.py"
        return base
    if exp_d > date.today() + timedelta(days=420):
        base["note"] = "event > 14 mnd ute, hopper over"
        return base

    body = _fetch(url)
    if body is None:
        base["status"] = "fetch_failed"
        base["note"] = "kunne ikke hente URL"
        return base
    text = _strip_html(body)
    dates = _extract_dates(text, date.today().year)
    base["found"] = [d.isoformat() for d in dates[:5]]
    if exp_d in dates:
        base["status"] = "ok"
        return base
    if not dates:
        base["status"] = "no_dates"
        base["note"] = "ingen datoer funnet i synlig tekst"
    else:
        base["status"] = "mismatch"
        closest = min(dates, key=lambda d: abs((d - exp_d).days))
        if abs((closest - exp_d).days) <= 365:
            base["note"] = f"regex foreslaar: {closest.isoformat()}"
        else:
            base["note"] = "ingen narliggende dato funnet"

    if not claude_key or budget is None or budget[0] <= 0:
        return base
    chash = _content_hash(text)
    base["claude_hash"] = chash
    if cache and event.get("id") in cache:
        cached = cache[event["id"]]
        if cached.get("hash") == chash and cached.get("suggested"):
            base["claude_suggested"] = cached["suggested"]
            base["note"] += f" | Claude (cached): {cached['suggested']}"
            return base
    suggested = _ask_claude_for_date(claude_key, title, expected, text)
    budget[0] -= 1
    time.sleep(0.3)
    if suggested:
        base["claude_suggested"] = suggested
        base["note"] += f" | Claude: {suggested}"
        try:
            if date.fromisoformat(suggested) == exp_d:
                base["status"] = "ok"
                base["note"] = "bekreftet av Claude"
        except ValueError:
            pass
    else:
        base["note"] += " | Claude: ukjent"
    return base


def verify_all_events(max_workers: int = 6, use_claude: bool = True) -> dict:
    """Verifiser alle kuraterte events. Skriver til event_verify.json."""
    from . import events as ev_mod
    raw_events = ev_mod.load_events()
    claude_key = _resolve_claude_key() if use_claude else ""
    cache = _load_cache() if claude_key else {}
    budget = [CLAUDE_MAX_CALLS if claude_key else 0]
    items = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {
            pool.submit(check_event, e, claude_key, cache, budget): e
            for e in raw_events
        }
        for fut in as_completed(futs):
            try:
                items.append(fut.result())
            except Exception as e:
                ev = futs[fut]
                items.append({
                    "id": ev.get("id"), "title": ev.get("title"),
                    "url": ev.get("url"), "expected": ev.get("event_date"),
                    "found": [], "status": "error",
                    "note": f"{type(e).__name__}: {e}",
                })
    items.sort(key=lambda x: (x["status"], x.get("title") or ""))
    counts = {}
    for i in items:
        counts[i["status"]] = counts.get(i["status"], 0) + 1
    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "counts": counts,
        "claude_calls_remaining": budget[0],
        "items": items,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    rep = verify_all_events()
    print(f"Verifisert {rep['total']} events:")
    for status, n in rep["counts"].items():
        print(f"  {status}: {n}")
    mismatches = [i for i in rep["items"] if i["status"] == "mismatch"]
    if mismatches:
        print(f"\n{len(mismatches)} mismatches:")
        for m in mismatches[:15]:
            extra = m.get("claude_suggested") or m.get("note", "")
            print(f"  {m['expected']} -> {extra}")
            print(f"    {m['title'][:60]}")
            print(f"    {m['url']}")
