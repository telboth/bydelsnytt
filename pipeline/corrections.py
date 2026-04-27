"""Manuelle/auto-genererte korreksjoner som overstyrer events.py.

Bakgrunn: events.py er kilde-koden for kuraterte arrangementer og kan ikke
auto-redigeres trygt (krever Git push, manuell vurdering ved konflikt).
Men event_verify.py oppdager ofte at events.py har feil dato — typisk fordi
arrangoeren har publisert eksakt dato etter at vi gjettet 'siste loerdag i
september'.

Loesning: event_corrections.json holder { story_id -> {field, corrected, ...} }
som anvendes etter cache.merge() i pipelinen. Korreksjonene persisterer
mellom kjoeringer og overlever overskriving fra events.py.

Filen kan ogsaa redigeres manuelt om noen vil overstyre noe spesifikt.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


CORRECTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "event_corrections.json"
)


def load() -> dict:
    if not CORRECTIONS_PATH.exists():
        return {"schemaVersion": 1, "updatedAt": None, "corrections": {}}
    try:
        return json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schemaVersion": 1, "updatedAt": None, "corrections": {}}


def save(data: dict) -> None:
    data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    CORRECTIONS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_correction(data: dict, story_id: str, field: str,
                   original: str, corrected: str, reason: str) -> bool:
    """Lagre en ny korreksjon. Returnerer True hvis ny eller endret,
    False hvis allerede registrert."""
    corrections = data.setdefault("corrections", {})
    existing = corrections.get(story_id)
    if existing and existing.get("corrected") == corrected:
        return False
    corrections[story_id] = {
        "field": field,
        "original": original,
        "corrected": corrected,
        "reason": reason,
        "appliedAt": datetime.now(timezone.utc).isoformat(),
    }
    return True


def apply(stories: list[dict], data: dict | None = None) -> int:
    """Anvend korreksjoner paa en liste stories. Muterer in-place.

    Returnerer antall stories som ble endret.
    """
    if data is None:
        data = load()
    corrections = data.get("corrections") or {}
    if not corrections:
        return 0
    by_id = {s.get("id"): s for s in stories if s.get("id")}
    n = 0
    for sid, c in corrections.items():
        s = by_id.get(sid)
        if not s:
            continue
        field = c.get("field")
        new_val = c.get("corrected")
        if not field or new_val is None:
            continue
        if s.get(field) == new_val:
            continue
        s[field] = new_val
        # event_date og date_iso hoerer sammen — synkroniser
        if field == "event_date":
            s["date_iso"] = new_val
        n += 1
    return n


if __name__ == "__main__":
    data = load()
    cnt = len(data.get("corrections") or {})
    print(f"event_corrections.json: {cnt} korreksjoner registrert")
    for sid, c in (data.get("corrections") or {}).items():
        print(f"  {sid}: {c['field']} '{c['original']}' -> '{c['corrected']}'")
        print(f"    reason: {c.get('reason', '')}")
