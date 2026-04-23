"""Cache og de-duplisering av saker via stories.json.

Formål: behold historikk mellom kjøringer, slik at enkeltsaker ikke forsvinner
bare fordi de er rullet ut av en RSS-feed. Merge-strategien er enkel:

* Ny sak (ukjent id): legges til
* Kjent id: oppdater felt som title, summary, category, published_iso — men
  behold tidligere fetched_at som "first_seen" og oppdater "last_seen".
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CACHE_PATH = Path(__file__).resolve().parent.parent / "stories.json"
DEFAULT_MAX_AGE_DAYS = 120


def load(path: Path = CACHE_PATH) -> dict:
    """Returner hele cache-strukturen. Oppretter tom struktur om filen mangler."""
    if not path.exists():
        return {"schemaVersion": 1, "updatedAt": None, "stories": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(cache: dict, path: Path = CACHE_PATH) -> None:
    cache["updatedAt"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def merge(existing: list[dict], incoming: Iterable[dict]) -> list[dict]:
    """Returner en oppdatert liste saker etter merge av nye mot eksisterende."""
    by_id = {s["id"]: dict(s) for s in existing}
    now = datetime.now(timezone.utc).isoformat()

    for new in incoming:
        sid = new["id"]
        if sid in by_id:
            old = by_id[sid]
            # Oppdater felt som kan endres. Inkluderer lat/lng/location_precise
            # slik at oppdateringer i locations.py forplanter seg til eksisterende
            # saker og ikke bare nye.
            old.update({k: new[k] for k in (
                "title", "url", "summary", "category", "published_iso",
                "date_iso", "source", "source_id", "bydel",
                "lat", "lng", "location_precise",
            ) if k in new})
            old["last_seen_iso"] = now
            if "first_seen_iso" not in old:
                old["first_seen_iso"] = old.get("fetched_at_iso") or now
        else:
            row = dict(new)
            row["first_seen_iso"] = row.get("fetched_at_iso") or now
            row["last_seen_iso"] = now
            by_id[sid] = row

    return list(by_id.values())


def prune(stories: list[dict], max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> list[dict]:
    """Fjern saker eldre enn max_age_days basert på date_iso."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=max_age_days)).isoformat()
    return [s for s in stories if (s.get("date_iso") or "9999") >= cutoff]


def replace_and_save(stories: list[dict]) -> None:
    """Bekvemmelighets-funksjon: erstatt hele listen og skriv."""
    cache = {"schemaVersion": 1, "stories": stories}
    save(cache)
