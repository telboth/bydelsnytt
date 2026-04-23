"""Orkestrator: hent -> klassifiser -> merge -> dedup -> lagre stories.json.

Denne kjoeres av scheduled task foer build.py. Kan ogsaa kjoeres manuelt:
    python3 -m pipeline.run
"""
from __future__ import annotations

from collections import Counter

from . import cache, classify, dedup, events, fetcher, health, locations


def run() -> dict:
    """Hent alle kilder + kuraterte events, klassifiser, merge, skriv stories.json."""
    health_data = health.load()
    raw = [s.to_dict() for s in fetcher.fetch_all(health_data)]
    raw.extend(events.load_events())
    classified = classify.classify_all(raw)
    enriched = locations.enrich(classified)

    existing = cache.load()["stories"]
    merged = cache.merge(existing, enriched)
    pruned = cache.prune(merged)
    deduped = dedup.deduplicate(pruned)
    cache.replace_and_save(deduped)
    health.save(health_data)

    stale = health.stale_sources(health_data)
    hidden = sum(1 for s in deduped if s.get("hidden"))
    stats = {
        "fetched": len(raw),
        "existing": len(existing),
        "after_merge": len(merged),
        "after_prune": len(pruned),
        "after_dedup_hidden": hidden,
        "per_bydel": dict(Counter(s.get("bydel") for s in deduped
                                  if not s.get("hidden"))),
        "per_category": dict(Counter(s.get("category") for s in deduped
                                     if not s.get("hidden"))),
        "per_source": dict(Counter(s.get("source_id") for s in deduped)),
        "precise_locations": sum(1 for s in deduped
                                 if s.get("location_precise") and not s.get("hidden")),
        "stale_sources": [s["id"] for s in stale],
    }
    return stats


if __name__ == "__main__":
    stats = run()
    print("\n=== run.py done ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
