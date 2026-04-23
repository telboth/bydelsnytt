"""Kildehelsesjekk: registrer per-kilde-statistikk for hver pipeline-kjøring.

Formål: gjøre det synlig i UI når en kilde slutter å levere. Lagrer en
kompakt record per source_id i source_health.json:

{
  "schemaVersion": 1,
  "updatedAt": "...",
  "sources": {
      "skeid": {
          "name": "Skeid",
          "last_attempt_iso": "...",
          "last_success_iso": "...",
          "last_count": 20,
          "last_error": null,
          "consecutive_empty_runs": 0,
          "history": [{"at": "...", "count": 20}, ...]   # siste 14 kjøringer
      },
      ...
  }
}

Bygg.py leser filen og viser en banner når en kilde har vært tom siden en
terskel (STALE_DAYS = 7).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


HEALTH_PATH = Path(__file__).resolve().parent.parent / "source_health.json"
MAX_HISTORY = 14
STALE_DAYS = 7


def load() -> dict:
    if not HEALTH_PATH.exists():
        return {"schemaVersion": 1, "updatedAt": None, "sources": {}}
    try:
        return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schemaVersion": 1, "updatedAt": None, "sources": {}}


def save(data: dict) -> None:
    data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    HEALTH_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record(data: dict, source_id: str, name: str, count: int,
           error: str | None = None) -> None:
    """Oppdater health-record for en enkelt kilde etter én fetch-runde."""
    now = datetime.now(timezone.utc).isoformat()
    sources = data.setdefault("sources", {})
    entry = sources.get(source_id) or {}
    entry["name"] = name
    entry["last_attempt_iso"] = now
    entry["last_count"] = count
    entry["last_error"] = error
    if count > 0 and not error:
        entry["last_success_iso"] = now
        entry["consecutive_empty_runs"] = 0
    else:
        entry["consecutive_empty_runs"] = int(
            entry.get("consecutive_empty_runs", 0)
        ) + 1
    hist = entry.setdefault("history", [])
    hist.append({"at": now, "count": count, "error": error})
    # behold kun siste N kjøringer for å holde filen liten
    entry["history"] = hist[-MAX_HISTORY:]
    sources[source_id] = entry


def stale_sources(data: dict, stale_days: int = STALE_DAYS) -> list[dict]:
    """Returner liste over kilder som ikke har levert på >= stale_days dager."""
    from datetime import datetime as dt
    cutoff = dt.now(timezone.utc).timestamp() - stale_days * 86400
    out = []
    for sid, entry in (data.get("sources") or {}).items():
        last_ok = entry.get("last_success_iso")
        if not last_ok:
            out.append({"id": sid, "name": entry.get("name", sid),
                        "last_success_iso": None,
                        "consecutive_empty_runs": entry.get(
                            "consecutive_empty_runs", 0)})
            continue
        try:
            last_ts = dt.fromisoformat(last_ok.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if last_ts < cutoff:
            out.append({"id": sid, "name": entry.get("name", sid),
                        "last_success_iso": last_ok,
                        "consecutive_empty_runs": entry.get(
                            "consecutive_empty_runs", 0)})
    return out


if __name__ == "__main__":
    data = load()
    print(f"Kilder registrert: {len(data.get('sources') or {})}")
    for sid, entry in (data.get("sources") or {}).items():
        print(f"  {sid}: {entry.get('last_count')} saker, "
              f"last_success={entry.get('last_success_iso')}")
    stale = stale_sources(data)
    if stale:
        print(f"\n{len(stale)} kilder er stale (>{STALE_DAYS} dager):")
        for s in stale:
            print(f"  - {s['name']} ({s['id']})")
