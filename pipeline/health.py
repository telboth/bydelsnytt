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


def record_new_stories(data: dict, new_per_source: dict) -> None:
    """Etter merge: oppdater last_new_story_iso for kilder som leverte
    minst én genuint ny sak (id som ikke fantes i cache fra foer).

    Stille-doed-deteksjon: en kilde som svarer 200 OK med samme 10 saker
    hver dag har last_success_iso = i dag, men last_new_story_iso flere
    uker tilbake — og er reelt "fryst".
    """
    now = datetime.now(timezone.utc).isoformat()
    sources = data.setdefault("sources", {})
    for sid, n in (new_per_source or {}).items():
        if n <= 0:
            continue
        entry = sources.setdefault(sid, {"name": sid})
        entry["last_new_story_iso"] = now
        entry["last_new_story_count"] = int(n)


def stale_sources(data: dict, stale_days: int = STALE_DAYS) -> list[dict]:
    """Returner liste over kilder som er "stale".

    En kilde er stale enten naar:
      - last_success_iso er eldre enn stale_days, ELLER
      - last_new_story_iso er eldre enn stale_days * 2 (stille-doed-deteksjon
        - kilden svarer OK, men leverer kun saker vi har sett foer)
    """
    from datetime import datetime as dt
    now_ts = dt.now(timezone.utc).timestamp()
    cutoff_ok = now_ts - stale_days * 86400
    cutoff_new = now_ts - stale_days * 2 * 86400
    out = []
    for sid, entry in (data.get("sources") or {}).items():
        last_ok = entry.get("last_success_iso")
        last_new = entry.get("last_new_story_iso")
        reason = None
        if not last_ok:
            reason = "aldri_levert"
        else:
            try:
                last_ok_ts = dt.fromisoformat(
                    last_ok.replace("Z", "+00:00")
                ).timestamp()
                if last_ok_ts < cutoff_ok:
                    reason = "ingen_kontakt"
            except ValueError:
                pass
        if reason is None and last_new:
            try:
                last_new_ts = dt.fromisoformat(
                    last_new.replace("Z", "+00:00")
                ).timestamp()
                if last_new_ts < cutoff_new:
                    reason = "stille_doed"
            except ValueError:
                pass
        if reason:
            out.append({
                "id": sid,
                "name": entry.get("name", sid),
                "last_success_iso": last_ok,
                "last_new_story_iso": last_new,
                "reason": reason,
                "consecutive_empty_runs": entry.get(
                    "consecutive_empty_runs", 0
                ),
            })
    return out


if __name__ == "__main__":
    data = load()
    print(f"Kilder registrert: {len(data.get('sources') or {})}")
    stale = stale_sources(data)
    if stale:
        print(f"\n{len(stale)} kilder er stale:")
        for s in stale:
            print(f"  - {s['name']} ({s['id']}): {s['reason']}")
    else:
        print("Alle kilder leverer ferskt.")
