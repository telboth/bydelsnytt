"""RSS 2.0 feed for Bydelsnytt Oslo.

Genererer feed.xml med de 100 nyeste sakene. Hver sak har bydel som
<category>-tag slik at abonnenter kan filtrere per bydel i klienten sin.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import formatdate
from html import escape as _esc
from xml.sax.saxutils import escape as _xml_esc

SITE_URL = "https://telboth.github.io/bydelsnytt/"
FEED_URL = "https://telboth.github.io/bydelsnytt/feed.xml"
FEED_TITLE = "Bydelsnytt Oslo"
FEED_DESCRIPTION = (
    "Daglig oppdatert lokalnytt fra alle 15 bydeler i Oslo — "
    "samlet fra RSS, kommunale kilder og håndkuraterte arrangementer."
)
MAX_ITEMS = 100


def _rfc822(iso: str | None) -> str:
    if not iso:
        return formatdate(timeval=None, localtime=False, usegmt=True)
    try:
        # Tåler både "YYYY-MM-DD" og full ISO
        if len(iso) == 10:
            dt = datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return formatdate(dt.timestamp(), localtime=False, usegmt=True)
    except (ValueError, TypeError):
        return formatdate(timeval=None, localtime=False, usegmt=True)


def _sort_key(s: dict) -> str:
    # Nyeste først. Bruk first_seen hvis tilgjengelig (mer ærlig for curated events).
    return (
        s.get("first_seen_iso")
        or s.get("published_iso")
        or s.get("date_iso")
        or "0000-00-00"
    )


def build_feed(stories: list[dict]) -> str:
    """Lag RSS 2.0-XML fra stories-listen."""
    visible = [s for s in stories if not s.get("hidden")]
    visible.sort(key=_sort_key, reverse=True)
    items = visible[:MAX_ITEMS]

    now = formatdate(timeval=None, localtime=False, usegmt=True)
    last_build = items[0].get("first_seen_iso") if items else None

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">',
        '  <channel>',
        f'    <title>{_xml_esc(FEED_TITLE)}</title>',
        f'    <link>{_xml_esc(SITE_URL)}</link>',
        f'    <description>{_xml_esc(FEED_DESCRIPTION)}</description>',
        '    <language>nb-NO</language>',
        f'    <lastBuildDate>{_rfc822(last_build) if last_build else now}</lastBuildDate>',
        f'    <atom:link href="{_xml_esc(FEED_URL)}" rel="self" type="application/rss+xml" />',
        '    <generator>Bydelsnytt Oslo pipeline</generator>',
    ]

    for s in items:
        title = s.get("title") or "(uten tittel)"
        link = s.get("url") or SITE_URL
        summary = s.get("summary") or ""
        bydel = s.get("bydel") or ""
        category = s.get("category") or ""
        source_name = s.get("source") or ""
        pub_date = _rfc822(
            s.get("first_seen_iso")
            or s.get("published_iso")
            or s.get("date_iso")
        )
        # GUID: url er stabil nok
        guid = link

        # Legg bydel + kategori som <category>-tagger
        category_tags = "".join(
            f'      <category>{_xml_esc(c)}</category>\n'
            for c in (bydel, category) if c
        )

        desc_html = summary
        if source_name:
            desc_html = f"<p><em>{_esc(source_name)}</em></p>\n" + _esc(summary)

        parts.append(
            "    <item>\n"
            f"      <title>{_xml_esc(title)}</title>\n"
            f"      <link>{_xml_esc(link)}</link>\n"
            f"      <guid isPermaLink=\"true\">{_xml_esc(guid)}</guid>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <dc:creator>{_xml_esc(source_name)}</dc:creator>\n"
            f"{category_tags}"
            f"      <description>{_xml_esc(desc_html)}</description>\n"
            "    </item>"
        )

    parts.append("  </channel>")
    parts.append("</rss>")
    return "\n".join(parts) + "\n"
