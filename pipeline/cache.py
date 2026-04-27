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
DEFAULT_MAX_AGE_DAYS = 90


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
            #
            # MERK: date_iso og published_iso er bevisst UTELATT. Flere scrapere
            # (IL Try, noen HTML-kilder) stamper datoen til fetch-tidspunktet
            # fordi kilden ikke eksponerer publiseringsdato. Hvis vi oppdaterer
            # disse feltene her, vil enhver kjent sak få ny dato hver kjoering
            # og feilaktig merkes som "ferskt". Foerste observerte dato er det
            # noermeste vi kommer sannheten og bevares.
            old.update({k: new[k] for k in (
                "title", "url", "summary", "category",
                "source", "source_id", "bydel",
                "lat", "lng", "location_precise",
                "event_date",
            ) if k in new})
            # Fyll inn date_iso/published_iso bare hvis de mangler fra foer
            for field in ("date_iso", "published_iso"):
                if not old.get(field) and field in new:
                    old[field] = new[field]
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


def count_new_per_source(existing: list[dict], incoming: Iterable[dict]) -> dict:
    """Tell hvor mange GENUINT NYE saker (id ikke i cache fra foer) hver
    source_id leverte. Brukes til stille-doed-deteksjon i health.py."""
    seen = {s["id"] for s in existing}
    out: dict = {}
    for s in incoming:
        if s.get("id") in seen:
            continue
        sid = s.get("source_id") or "unknown"
        out[sid] = out.get(sid, 0) + 1
    return out


def replace_and_save(stories: list[dict]) -> None:
    """Bekvemmelighets-funksjon: erstatt hele listen og skriv."""
    CACHE_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "stories": stories,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
