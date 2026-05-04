"""Orkestrator: hent -> klassifiser -> merge -> dedup -> lagre stories.json.

Denne kjoeres av scheduled task foer build.py. Kan ogsaa kjoeres manuelt:
    python3 -m pipeline.run
"""
from __future__ import annotations

from collections import Counter

from . import cache, classify, corrections, dedup, events, fetcher, health, images, locations


def run() -> dict:
    """Hent alle kilder + kuraterte events, klassifiser, merge, skriv stories.json."""
    health_data = health.load()
    raw = [s.to_dict() for s in fetcher.fetch_all(health_data)]
    raw.extend(events.load_events())
    classified = classify.classify_all(raw)
    enriched = locations.enrich(classified)

    existing = cache.load()["stories"]
    # Stille-doed-deteksjon: tell hvor mange genuint nye saker hver kilde
    # leverte for helse-rapportering.
    new_per_src = cache.count_new_per_source(existing, enriched)
    health.record_new_stories(health_data, new_per_src)
    merged = cache.merge(existing, enriched)
    pruned = cache.prune(merged)
    deduped = dedup.deduplicate(pruned)
    clustered = dedup.cluster_topics(deduped)
    # Anvend dato-korreksjoner fra event_corrections.json (oppdateres av
    # event_verify.py). Disse overlever overskriving fra events.py paa
    # hver pipeline-run.
    corr_count = corrections.apply(clustered)
    if corr_count:
        print(f"[run] {corr_count} dato-korreksjoner anvendt fra event_corrections.json")
    deduped = clustered
    image_stats = images.enrich_images(deduped)
    print(f"[run] image enrich: {image_stats}")

    # Rydd foreldreloese entries i images.json (saker som er blitt prunet bort).
    img_cache = images.load_cache()
    story_urls = {(s.get("url") or "").strip() for s in deduped}
    removed = images.prune_orphan_images(img_cache, story_urls)
    if removed:
        images.save_cache(img_cache)
    image_stats["orphans_removed"] = removed

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
        "image_enrich": image_stats,
        "corrections_applied": corr_count,
    }
    return stats


if __name__ == "__main__":
    stats = run()
    print("\n=== run.py done ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
