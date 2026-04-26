"""Kjoer fetch + merge + save uten image-enrich (for hastighet i splittet kjoering)."""
from pipeline import cache, classify, dedup, events, fetcher, health, locations

health_data = health.load()
raw = [s.to_dict() for s in fetcher.fetch_all(health_data)]
raw.extend(events.load_events())
classified = classify.classify_all(raw)
enriched = locations.enrich(classified)

existing = cache.load()["stories"]
# Stille-doed-deteksjon: tell hvor mange genuint nye saker hver kilde leverte
new_per_src = cache.count_new_per_source(existing, enriched)
health.record_new_stories(health_data, new_per_src)
merged = cache.merge(existing, enriched)
pruned = cache.prune(merged)
deduped = dedup.deduplicate(pruned)
clustered = dedup.cluster_topics(deduped)
cache.replace_and_save(clustered)
health.save(health_data)
topic_count = len({s["topic_id"] for s in clustered if s.get("topic_id")})
print(f"[fetch-only] lagret {len(clustered)} saker til stories.json "
      f"({topic_count} topic-klynger)")
print(f"[fetch-only] {sum(new_per_src.values())} genuint nye saker fra "
      f"{len(new_per_src)} kilder")
