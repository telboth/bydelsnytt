"""AI-TL;DR for toppsaker via Claude Haiku.

Genererer korte (1-2 setninger) norske sammendrag av topp-saker. Lagres i
tldr.json med cache-key = story.id + content-hash, slik at samme sak ikke
sammendraes om igjen mellom kjoeringer.

Skips hele opplegget hvis ANTHROPIC_API_KEY ikke er satt — designet til aa
vaere en gratisbillig "nice to have" som ikke skal blokkere bygget.

Modell: claude-haiku-4-5-20251001 (lavest pris, mer enn nok for to-setnings-
sammendrag paa norsk).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

CACHE_PATH = Path(__file__).resolve().parent.parent / "tldr.json"
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 220
TIMEOUT_S = 20
# Begrens til topp N saker per kjoering — selv om vi har cache vil dette
# styre hvor mange API-calls vi maks gjoer paa en kjoering.
MAX_PER_RUN = 12

SYSTEM_PROMPT = (
    "Du oppsummerer norske lokalnyheter for en bydelsnytt-side. "
    "Skriv ETT eller TO korte setninger (totalt under 220 tegn) paa norsk "
    "bokmaal som forklarer hva saken handler om og hvorfor den er relevant "
    "for innbyggere i bydelen. Ikke bruk klikkagn, ikke gjenta tittelen "
    "ordrett, ikke spekuler. Svar med kun sammendraget, uten anfoerselstegn."
)


def _content_hash(story: dict) -> str:
    """Cache-noekkel paa innhold som tilsier nytt sammendrag hvis innholdet
    endres."""
    parts = (
        (story.get("title") or "")[:300],
        (story.get("summary") or "")[:500],
    )
    h = hashlib.sha1("␞".join(parts).encode("utf-8")).hexdigest()
    return h[:16]


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"schemaVersion": 1, "items": {}}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": 1, "items": {}}


def _save_cache(data: dict) -> None:
    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _build_prompt(story: dict) -> str:
    title = (story.get("title") or "").strip()
    summary = (story.get("summary") or "").strip()
    bydel = (story.get("bydel") or "").strip()
    source = (story.get("source") or "").strip()
    return (
        f"Bydel: {bydel}\nKilde: {source}\nTittel: {title}\n\n"
        f"Innhold (utdrag):\n{summary[:1200]}\n\n"
        "Skriv et kort sammendrag (1-2 setninger, < 220 tegn)."
    )


def _call_api(api_key: str, story: dict) -> str | None:
    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": _build_prompt(story)}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[tldr] HTTPError {e.code} for {story.get('id')}", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[tldr] feil {type(e).__name__}: {e}", file=sys.stderr)
        return None
    # response: { content: [{ type: "text", text: "..." }] }
    blocks = payload.get("content") or []
    for blk in blocks:
        if blk.get("type") == "text":
            text = (blk.get("text") or "").strip()
            # rens mulige anfoerselstegn rundt
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1].strip()
            return text or None
    return None


def enrich_top_stories(stories: Iterable[dict],
                       max_calls: int = MAX_PER_RUN) -> dict:
    """Generer/hent TL;DR for inntil max_calls saker. Returner dict
    {story_id: tldr_text}. Cache lagres til tldr.json.

    Kalleren bestemmer hvilke saker som er "topp" — vi gjor ikke prioritering
    her, kun caching og API-call.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cache = _load_cache()
    items = cache.setdefault("items", {})
    out: dict[str, str] = {}
    calls_made = 0
    new_entries = 0

    for story in stories:
        sid = story.get("id")
        if not sid:
            continue
        chash = _content_hash(story)
        cached = items.get(sid)
        if cached and cached.get("hash") == chash and cached.get("text"):
            out[sid] = cached["text"]
            continue
        # Trenger ny generering — krever API-key
        if not api_key:
            continue
        if calls_made >= max_calls:
            break
        text = _call_api(api_key, story)
        calls_made += 1
        if text:
            items[sid] = {
                "hash": chash,
                "text": text,
                "model": MODEL,
                "ts": int(time.time()),
            }
            out[sid] = text
            new_entries += 1
        # Liten pause for aa unngaa rate-limit
        time.sleep(0.3)

    if new_entries:
        _save_cache(cache)
    if api_key:
        print(
            f"[tldr] {len(out)} sammendrag levert "
            f"({new_entries} nye API-call, {calls_made} totalt forsoek)"
        )
    else:
        print(
            f"[tldr] ANTHROPIC_API_KEY mangler — bruker {len(out)} cache-treff "
            "(0 nye)",
            file=sys.stderr,
        )
    return out


def get_cached(story_id: str) -> str | None:
    """Slaa opp en cache-tekst uten API-call."""
    cache = _load_cache()
    item = cache.get("items", {}).get(story_id)
    if not item:
        return None
    return item.get("text")


if __name__ == "__main__":
    # Manuell test: generer TL;DR for de 5 forste saksene i stories.json
    cache_path = Path(__file__).resolve().parent.parent / "stories.json"
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    stories = data["stories"][:5]
    res = enrich_top_stories(stories)
    for s in stories:
        print(f"\n{s['title'][:70]}")
        print(f"  -> {res.get(s['id'], '(none)')}")
