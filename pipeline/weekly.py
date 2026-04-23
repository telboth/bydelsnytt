"""Ukentlig digest — lager weekly/YYYY-wWW.html hver fredag.

Leser stories.json, filtrerer siste 7 dager, grupperer per bydel og
viser topp-5 per bydel. Arkivet bygges opp over tid slik at man kan se
trender: hvilke bydeler er aktive, hvilke kategorier dominerer, osv.

Kan kalles fra cron/scheduled task:
    python3 -m pipeline.weekly

Eller importeres:
    from pipeline.weekly import write_weekly_digest
    path = write_weekly_digest()  # returnerer Path til generert fil
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape as esc
from pathlib import Path

from . import cache

BASE_DIR = Path(__file__).resolve().parent.parent
WEEKLY_DIR = BASE_DIR / "weekly"
INDEX_FILE = WEEKLY_DIR / "index.html"

TOP_N_PER_BYDEL = 5
LOOKBACK_DAYS = 7

BYDEL_ORDER = [
    "Alna", "Bjerke", "Frogner", "Gamle Oslo", "Grorud", "Grünerløkka",
    "Nordre Aker", "Nordstrand", "Sagene", "St. Hanshaugen", "Stovner",
    "Søndre Nordstrand", "Ullern", "Vestre Aker", "Østensjø",
]

CATEGORY_LABELS = {
    "politikk": "Politikk", "skole": "Skole", "idrett": "Idrett",
    "kultur": "Kultur", "trafikk": "Trafikk", "helse": "Helse",
    "naering": "Næring", "sikkerhet": "Sikkerhet",
    "arrangement": "Arrangement", "annet": "Annet",
}


def _recent_stories(stories: list[dict], lookback_days: int = LOOKBACK_DAYS):
    today = date.today()
    cutoff = today - timedelta(days=lookback_days)
    out = []
    for s in stories:
        if s.get("hidden"):
            continue
        iso = s.get("first_seen_iso") or s.get("published_iso") or s.get("date_iso")
        if not iso:
            continue
        try:
            d = datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            try:
                d = datetime.strptime(iso[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
        if cutoff <= d <= today:
            out.append((d, s))
    return out


def _week_label(today: date | None = None) -> tuple[int, int, str]:
    today = today or date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return iso_year, iso_week, f"{iso_year}-w{iso_week:02d}"


def _story_card(s: dict) -> str:
    title = esc(s.get("title", ""))
    url = esc(s.get("url", ""))
    source = esc(s.get("source", ""))
    cat = s.get("category") or "annet"
    cat_label = esc(CATEGORY_LABELS.get(cat, cat))
    date_iso = esc(s.get("date_iso", "") or "")
    return f'''        <li class="item">
          <a href="{url}" target="_blank" rel="noopener">{title}</a>
          <div class="meta">
            <span class="src">{source}</span>
            <span class="sep">·</span>
            <span class="pill {esc(cat)}">{cat_label}</span>
            <span class="sep">·</span>
            <span class="date">{date_iso}</span>
          </div>
        </li>'''


def build_weekly_html(stories: list[dict], today: date | None = None) -> tuple[str, str]:
    """Returns (slug, html) for this week."""
    today = today or date.today()
    year, week_no, slug = _week_label(today)
    recent = _recent_stories(stories)
    # Sort by date desc
    recent.sort(key=lambda t: t[0], reverse=True)

    per_bydel: dict[str, list[dict]] = defaultdict(list)
    for d, s in recent:
        per_bydel[s.get("bydel") or ""].append(s)

    cat_totals = Counter(s.get("category") or "annet" for _, s in recent)

    # Header stats
    total_sager = len(recent)
    num_bydeler = sum(1 for b in BYDEL_ORDER if per_bydel.get(b))

    sections = []
    for b in BYDEL_ORDER:
        items = per_bydel.get(b, [])
        if not items:
            sections.append(
                f'<section class="bydel empty"><h2>{esc(b)}</h2>'
                f'<p class="empty-note">Ingen nye saker denne uka.</p></section>'
            )
            continue
        top = items[:TOP_N_PER_BYDEL]
        cards = "\n".join(_story_card(s) for s in top)
        sections.append(
            f'<section class="bydel">\n'
            f'  <h2>{esc(b)} <small>{len(items)} sak{"er" if len(items) != 1 else ""}</small></h2>\n'
            f'  <ul class="items">\n{cards}\n  </ul>\n'
            f'</section>'
        )

    cat_chips = "\n".join(
        f'  <span class="chip cat-{esc(c)}">{esc(CATEGORY_LABELS.get(c, c))}: {n}</span>'
        for c, n in sorted(cat_totals.items(), key=lambda x: -x[1])
    )

    html = f'''<!DOCTYPE html>
<html lang="nb"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bydelsnytt Oslo — uke {week_no}, {year}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
       max-width: 920px; margin: 0 auto; padding: 24px;
       background: #fafaf9; color: #222; line-height: 1.55; }}
h1 {{ font-size: 24px; margin: 0 0 4px 0; }}
h2 {{ font-size: 17px; margin: 22px 0 8px 0; }}
h2 small {{ font-weight: 400; color: #888; font-size: 13px; }}
.byline {{ color: #666; font-size: 14px; margin-bottom: 18px; }}
.back {{ display: inline-block; margin-bottom: 14px; font-size: 14px;
         color: #1862a8; text-decoration: none; }}
.back:hover {{ text-decoration: underline; }}
.summary {{ background: #fff; border: 1px solid #e5e5e4; border-radius: 10px;
            padding: 14px 18px; margin: 14px 0 28px; }}
.summary p {{ margin: 0 0 10px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{ font-size: 12px; padding: 3px 10px; border-radius: 999px;
         background: #eef2f7; color: #33485f; }}
.chip.cat-idrett {{ background: #e8f6ec; color: #1f6d3a; }}
.chip.cat-kultur {{ background: #fff3d9; color: #8a5a00; }}
.chip.cat-trafikk {{ background: #ffe8e4; color: #9c2a12; }}
.chip.cat-politikk {{ background: #f3e8ff; color: #6b21a8; }}
.chip.cat-skole {{ background: #e7f2ff; color: #1a4f8b; }}
.chip.cat-naering {{ background: #e4f3ef; color: #1f6b5c; }}
.chip.cat-sikkerhet {{ background: #fce8e8; color: #9a1a1a; }}
.chip.cat-helse {{ background: #ffeaf1; color: #9c1f5a; }}
.chip.cat-arrangement {{ background: #fff0e4; color: #8a3a00; }}
.bydel {{ background: #fff; border: 1px solid #e5e5e4; border-radius: 10px;
          padding: 14px 18px; margin-bottom: 14px; }}
.bydel.empty {{ background: #fdfdfc; }}
.empty-note {{ color: #aaa; font-size: 13px; margin: 0; font-style: italic; }}
.items {{ list-style: none; padding: 0; margin: 0; }}
.item {{ padding: 9px 0; border-top: 1px solid #f0efec; }}
.item:first-child {{ border-top: none; padding-top: 4px; }}
.item a {{ color: #1862a8; text-decoration: none; font-weight: 500; }}
.item a:hover {{ text-decoration: underline; }}
.meta {{ font-size: 12px; color: #777; margin-top: 3px;
         display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
.meta .sep {{ color: #ccc; }}
.pill {{ font-size: 10px; padding: 1px 7px; border-radius: 999px;
         background: #eef2f7; color: #33485f;
         text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; }}
.pill.skole {{ background: #e7f2ff; color: #1a4f8b; }}
.pill.politikk {{ background: #f3e8ff; color: #6b21a8; }}
.pill.idrett {{ background: #e8f6ec; color: #1f6d3a; }}
.pill.kultur {{ background: #fff3d9; color: #8a5a00; }}
.pill.trafikk {{ background: #ffe8e4; color: #9c2a12; }}
.pill.naering {{ background: #e4f3ef; color: #1f6b5c; }}
.pill.sikkerhet {{ background: #fce8e8; color: #9a1a1a; }}
.pill.helse {{ background: #ffeaf1; color: #9c1f5a; }}
.pill.arrangement {{ background: #fff0e4; color: #8a3a00; }}
footer {{ margin-top: 28px; padding-top: 14px; border-top: 1px solid #e5e5e4;
          font-size: 13px; color: #888; }}
</style></head><body>
<a class="back" href="../">&larr; Tilbake til Bydelsnytt</a>
<h1>Bydelsnytt Oslo — uke {week_no}, {year}</h1>
<p class="byline">Ukeoppsummering av lokalnytt fra 15 Oslo-bydeler, siste 7 dager ({(today - timedelta(days=LOOKBACK_DAYS)).isoformat()} – {today.isoformat()}).</p>

<div class="summary">
<p><strong>{total_sager} saker</strong> registrert i {num_bydeler}/{len(BYDEL_ORDER)} bydeler denne uka.</p>
<div class="chips">
{cat_chips}
</div>
</div>

{chr(10).join(sections)}

<footer>Automatisk generert fra Bydelsnytt-pipelinen · <a href="../feed.xml">RSS</a> · <a href="index.html">Arkiv</a></footer>
</body></html>
'''
    return slug, html


def _rebuild_index() -> None:
    """Skriv weekly/index.html med liste over alle genererte uker."""
    WEEKLY_DIR.mkdir(exist_ok=True)
    files = sorted(
        [p for p in WEEKLY_DIR.iterdir()
         if p.suffix == ".html" and p.name not in ("index.html",)],
        reverse=True,
    )
    rows = "\n".join(
        f'<li><a href="{p.name}">{p.stem}</a></li>'
        for p in files
    )
    html = f'''<!DOCTYPE html>
<html lang="nb"><head>
<meta charset="utf-8"><title>Bydelsnytt Oslo — ukesarkiv</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif;
        max-width: 620px; margin: 0 auto; padding: 24px; color: #222; }}
h1 {{ font-size: 22px; }}
a {{ color: #1862a8; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
ul {{ line-height: 1.9; padding-left: 22px; }}
</style></head><body>
<a href="../">&larr; Tilbake til Bydelsnytt</a>
<h1>Ukesarkiv</h1>
<ul>{rows}</ul>
</body></html>
'''
    INDEX_FILE.write_text(html, encoding="utf-8")


def write_weekly_digest() -> Path:
    stories = cache.load().get("stories", [])
    slug, html = build_weekly_html(stories)
    WEEKLY_DIR.mkdir(exist_ok=True)
    path = WEEKLY_DIR / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    _rebuild_index()
    return path


if __name__ == "__main__":
    p = write_weekly_digest()
    print(f"Wrote: {p}")
    print(f"Index: {INDEX_FILE}")
