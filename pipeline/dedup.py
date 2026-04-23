"""Kryss-kilde-dedup: slaa sammen saker fra ulike kilder som dekker samme hendelse.

Ulike kilder (kondis, NRK, klubbsider) publiserer ofte om samme hendelse
med litt ulike titler. Vi beholder alle saker i stories.json (historikk), men
merker duplikater med hidden=True slik at build.py filtrerer dem bort paa
rendering. Paa den primaere saken fyller vi inn et extra_sources-felt slik at
brukeren kan se alle kildene.

Strategi:
* Normaliser titler: lowercase, fjern tegnsetting, stopord
* Token-basert Jaccard-likhet mellom par
* Dato-naerhet: kun par med date_iso innen 7 dager regnes som like
* Terskel: Jaccard >= 0.65

For hver match-klynge beholdes saken med hoeyest "source weight" som primaer.
Vekter kommer fra sources.py (RSS_SOURCES.weight), default 0.4.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta

from . import sources as S


SOURCE_WEIGHTS = {src["id"]: src.get("weight", 0.4)
                  for src in getattr(S, "RSS_SOURCES", [])}
SOURCE_WEIGHTS.update({src["id"]: src.get("weight", 0.4)
                       for src in getattr(S, "HTML_SOURCES", [])})
SOURCE_WEIGHTS["events"] = 1.0  # kuratert seed beholdes alltid

JACCARD_THRESHOLD = 0.65
DATE_WINDOW_DAYS = 7

_STOPWORDS = {
    "og", "i", "pa", "paa", "for", "til", "med", "av", "er", "en", "et",
    "den", "det", "som", "om", "ved", "har", "var", "fra", "da", "nye", "ny",
    "2024", "2025", "2026", "2027",
    "the", "and", "in", "on", "for", "to", "with", "of", "a",
}
_WORD_RE = re.compile(r"[a-z0-9\u00e6\u00f8\u00e5]+")


def _normalize(title: str) -> set[str]:
    if not title:
        return set()
    t = unicodedata.normalize("NFKD", title.lower())
    # kompakter diakritikk, men behold aeoeaa
    t = t.replace("\u00e6", "ae").replace("\u00f8", "oe").replace("\u00e5", "aa")
    tokens = set(_WORD_RE.findall(t))
    return {w for w in tokens if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _date_close(d1: str | None, d2: str | None,
                window: int = DATE_WINDOW_DAYS) -> bool:
    if not d1 or not d2:
        return True  # ukjent dato -> tillat match
    try:
        a = date.fromisoformat(d1[:10])
        b = date.fromisoformat(d2[:10])
    except ValueError:
        return True
    return abs((a - b).days) <= window


def _source_weight(story: dict) -> float:
    return SOURCE_WEIGHTS.get(story.get("source_id", ""), 0.4)


def _story_sort_key(story: dict) -> tuple:
    """Foretrekk: (a) events/kuraterte, (b) hoey source_weight,
    (c) tidligst first_seen_iso (originalen)."""
    return (
        -_source_weight(story),
        story.get("first_seen_iso") or story.get("fetched_at_iso") or "9999",
    )


def deduplicate(stories: list[dict]) -> list[dict]:
    """Returner stories der kryss-kilde-dubletter er markert hidden=True.

    Legger til felt paa "primaer"-saken:
      * dup_count: antall ekstra kilder
      * extra_sources: liste med {source_id, source, url} fra dupene
    Setter paa dubletter:
      * hidden: True
      * dup_of: ID-en til primary
    """
    # Fjern eventuelle gamle hidden/dup-markers slik at rekjøring er idempotent
    stories = [dict(s) for s in stories]
    for s in stories:
        s.pop("hidden", None)
        s.pop("dup_of", None)
        s.pop("dup_count", None)
        s.pop("extra_sources", None)

    # Pre-compute normalized tokens
    token_cache: dict[str, set[str]] = {}
    for s in stories:
        token_cache[s["id"]] = _normalize(s.get("title", ""))

    # Bucket paa bydel for aa unngaa O(n^2) paa hele settet
    by_bydel: dict[str, list[dict]] = defaultdict(list)
    for s in stories:
        by_bydel[s.get("bydel", "__none__")].append(s)

    marked_dup: dict[str, str] = {}  # dup_id -> primary_id
    clusters: dict[str, list[str]] = defaultdict(list)  # primary_id -> [dup_ids]

    for bydel, group in by_bydel.items():
        # Sortér for determinisme
        group = sorted(group, key=_story_sort_key)
        for i, cand in enumerate(group):
            if cand["id"] in marked_dup:
                continue
            cand_tokens = token_cache[cand["id"]]
            if len(cand_tokens) < 3:
                continue
            for other in group[i + 1:]:
                if other["id"] in marked_dup:
                    continue
                if cand.get("source_id") == other.get("source_id"):
                    continue  # samme kilde dedupes allerede av cache.merge
                other_tokens = token_cache[other["id"]]
                if len(other_tokens) < 3:
                    continue
                if not _date_close(cand.get("date_iso"), other.get("date_iso")):
                    continue
                sim = _jaccard(cand_tokens, other_tokens)
                if sim >= JACCARD_THRESHOLD:
                    marked_dup[other["id"]] = cand["id"]
                    clusters[cand["id"]].append(other["id"])

    if not marked_dup:
        return stories

    # Build index for quick lookup
    by_id = {s["id"]: s for s in stories}
    for primary_id, dup_ids in clusters.items():
        primary = by_id[primary_id]
        extras = []
        for did in dup_ids:
            d = by_id[did]
            extras.append({
                "source_id": d.get("source_id"),
                "source": d.get("source"),
                "url": d.get("url"),
            })
            d["hidden"] = True
            d["dup_of"] = primary_id
        primary["dup_count"] = len(dup_ids)
        primary["extra_sources"] = extras

    return stories


if __name__ == "__main__":
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "stories.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    before = len(data["stories"])
    deduped = deduplicate(data["stories"])
    hidden = sum(1 for s in deduped if s.get("hidden"))
    primaries = sum(1 for s in deduped if s.get("dup_count"))
    print(f"Før: {before} saker")
    print(f"Etter dedup: {hidden} markert som dublett, {primaries} primaersaker med ekstra kilder")
