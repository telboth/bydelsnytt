"""Hent nyhetssaker fra RSS-feeds og HTML-scrapers definert i sources.py."""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable, Optional

import feedparser

from . import sources as S


UA = "Mozilla/5.0 (bydelsnytt-bot; https://telboth.github.io/bydelsnytt/)"
SSL_CTX = ssl.create_default_context()


@dataclass
class RawStory:
    """Normalisert sak foer klassifisering og merge."""
    id: str
    bydel: str
    title: str
    url: str
    source: str
    source_id: str
    published_iso: str
    date_iso: str
    summary: str
    category: str = "annet"
    fetched_at_iso: str = ""

    def to_dict(self):
        return asdict(self)


def _make_id(url: str, title: str) -> str:
    h = hashlib.sha1()
    h.update(url.lower().strip().encode())
    h.update(b"|")
    h.update(title.lower().strip().encode())
    return h.hexdigest()[:16]


def _parse_published(entry) -> tuple[str, str]:
    for key in ("published_parsed", "updated_parsed"):
        tm = entry.get(key)
        if tm:
            dt = datetime.fromtimestamp(time.mktime(tm), tz=timezone.utc)
            return dt.isoformat(), dt.date().isoformat()
    now = datetime.now(timezone.utc)
    return now.isoformat(), now.date().isoformat()


def _clean_summary(raw: str, max_chars: int = 600) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _fetch_rss(url: str, timeout: int = 15) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  [fetcher] WARN: could not fetch {url}: {e}")
        return None


def _fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            raw = r.read()
            return raw.decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  [fetcher] WARN: could not fetch {url}: {e}")
        return None


def fetch_from_rss(source: dict) -> Iterable[RawStory]:
    data = _fetch_rss(source["url"])
    if data is None:
        return
    feed = feedparser.parse(data)
    resolver = S.RESOLVERS[source["resolver"]]
    feed_title = feed.feed.get("title", source["id"])
    fetched_at = datetime.now(timezone.utc).isoformat()

    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue
        bydel = resolver(entry)
        if bydel == getattr(S, "SKIP", "__SKIP__"):
            continue  # resolver signaliserte at saken ikke er Oslo-relevant
        if bydel is None:
            bydel = source.get("bydel")
        if bydel is None:
            continue
        published_iso, date_iso = _parse_published(entry)
        summary = _clean_summary(entry.get("summary", ""))
        yield RawStory(
            id=_make_id(url, title),
            bydel=bydel,
            title=title,
            url=url,
            source=feed_title,
            source_id=source["id"],
            published_iso=published_iso,
            date_iso=date_iso,
            summary=summary,
            fetched_at_iso=fetched_at,
        )


# --- IL Try scraper --------------------------------------------------------
_ILTRY_TITLE_RE = re.compile(r'<h3 class="post-title">(?P<t>[^<]+)</h3>', re.DOTALL)
_ILTRY_INTRO_RE = re.compile(r'<div class="post-introtext">(?P<s>.*?)</div>', re.DOTALL)
_ILTRY_LINK_RE = re.compile(r'href="(?P<u>https?://il-try\.no/post/\d+)"')


def _iltry_parse_page(html: str) -> list[dict]:
    items: list[dict] = []
    for chunk in re.split(r'<div class="post-item">', html)[1:]:
        end = re.search(r'</section>|<ul class="uk-pagination">', chunk)
        scope = chunk[: end.start()] if end else chunk
        t = _ILTRY_TITLE_RE.search(scope)
        u = _ILTRY_LINK_RE.search(scope)
        if not (t and u):
            continue
        s = _ILTRY_INTRO_RE.search(scope)
        summary = _clean_summary(s.group("s")) if s else ""
        items.append({
            "title": t.group("t").strip(),
            "url": u.group("u").strip(),
            "summary": summary,
        })
    return items


def fetch_from_html_iltry(source: dict) -> Iterable[RawStory]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    now = datetime.now(timezone.utc)
    published_iso = now.isoformat()
    date_iso = now.date().isoformat()
    seen: set[str] = set()
    limit = source.get("limit") or 0
    emitted = 0
    for url in source["urls"]:
        if limit and emitted >= limit:
            break
        html = _fetch_html(url)
        if html is None:
            continue
        for it in _iltry_parse_page(html):
            if limit and emitted >= limit:
                break
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            emitted += 1
            yield RawStory(
                id=_make_id(it["url"], it["title"]),
                bydel=source["bydel"],
                title=it["title"],
                url=it["url"],
                source=source.get("name", source["id"]),
                source_id=source["id"],
                published_iso=published_iso,
                date_iso=date_iso,
                summary=it["summary"],
                fetched_at_iso=fetched_at,
            )


# --- Kondis.no scraper -----------------------------------------------------
_KONDIS_JSONLD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(?P<body>.*?)</script>',
    re.DOTALL,
)

_KONDIS_OSLO_VENUES = [
    ("holmenkollstafetten", "Frogner"),
    ("holmenkollmarsjen",   "Vestre Aker"),
    ("oslos bratteste",     "Vestre Aker"),
    ("ekeberg backyard",    "Gamle Oslo"),
    ("sentrumsl\u00f8p",    "Frogner"),
    ("oslo maraton",        "Frogner"),
    ("bygd\u00f8ymila",     "Frogner"),
    ("norway cup",          "Gamle Oslo"),
    ("sognsvann rundt",     "Nordre Aker"),
    ("holmenkollen",        "Vestre Aker"),
    ("tryvann",             "Vestre Aker"),
    ("frognerseteren",      "Vestre Aker"),
    ("sognsvann",           "Nordre Aker"),
    ("grefsenkollen",       "Nordre Aker"),
    ("nydalen",             "Nordre Aker"),
    ("kringsj\u00e5",       "Nordre Aker"),
    ("bygd\u00f8y",         "Frogner"),
    ("bislett",             "St. Hanshaugen"),
    ("voldsl\u00f8kka",     "Sagene"),
    ("bj\u00f8rvika",       "Gamle Oslo"),
    ("ekebergsletta",       "Gamle Oslo"),
    ("t\u00f8yen",          "Gamle Oslo"),
    ("holmlia",             "S\u00f8ndre Nordstrand"),
    ("furuset",             "Alna"),
    ("grorud",              "Grorud"),
    ("stovner",             "Stovner"),
    ("ullern",              "Ullern"),
    ("oslo",                "Frogner"),
]


def _kondis_pick_bydel(title: str) -> "Optional[str]":
    t = (title or "").lower()
    for needle, bydel in _KONDIS_OSLO_VENUES:
        if re.search(r'(?<![a-z\u00e6\u00f8\u00e5])' + re.escape(needle.lower()) + r'(?![a-z\u00e6\u00f8\u00e5])', t):
            return bydel
    order = sorted(S.BYDELER, key=lambda b: -len(b))
    for b in order:
        if re.search(r'(?<![a-z\u00e6\u00f8\u00e5])' + re.escape(b.lower()) + r'(?![a-z\u00e6\u00f8\u00e5])', t):
            return b
    return None


def _kondis_extract_articles(html: str) -> list[dict]:
    articles: list[dict] = []

    def _walk(node):
        if isinstance(node, dict):
            if node.get("@type") == "NewsArticle":
                h = (node.get("headline") or "").strip()
                u = (node.get("url") or "").strip()
                if h and u:
                    articles.append({"title": h, "url": u})
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    for m in _KONDIS_JSONLD_RE.finditer(html):
        body = m.group("body").strip()
        if "NewsArticle" not in body:
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        _walk(data)
    return articles


def fetch_from_html_kondis(source: dict) -> Iterable[RawStory]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    now = datetime.now(timezone.utc)
    published_iso = now.isoformat()
    date_iso = now.date().isoformat()
    seen: set[str] = set()
    limit = source.get("limit") or 0
    emitted = 0

    for url in source["urls"]:
        if limit and emitted >= limit:
            break
        html = _fetch_html(url)
        if html is None:
            continue
        for art in _kondis_extract_articles(html):
            if limit and emitted >= limit:
                break
            article_url = art["url"]
            if article_url.startswith("/"):
                article_url = "https://www.kondis.no" + article_url
            if not article_url.startswith("https://www.kondis.no/"):
                continue
            title = art["title"]
            if article_url in seen or len(title) < 10:
                continue
            seen.add(article_url)
            bydel = _kondis_pick_bydel(title)
            if bydel is None:
                continue
            emitted += 1
            yield RawStory(
                id=_make_id(article_url, title),
                bydel=bydel,
                title=title,
                url=article_url,
                source=source.get("name", source["id"]),
                source_id=source["id"],
                published_iso=published_iso,
                date_iso=date_iso,
                summary="",
                fetched_at_iso=fetched_at,
            )


# --- Oslo politidistrikt scraper ------------------------------------------
_POLITI_ARTICLE_RE = re.compile(
    r'href="(/nyheter-og-presse/oslo/nyhet/(\d{4}-\d{2}-\d{2})/[^"]+)"'
    r'[\s\S]{1,800}?<sds-heading[^>]*>\s*<span[^>]*>([^<]{5,200})</span>'
)


def fetch_from_html_politi(source: dict) -> Iterable[RawStory]:
    """Oslo politidistrikt - nyheter-og-presse/oslo.

    Siden bygges av Next.js men artikler er server-renderet i HTML med
    <sds-heading>-tittel og dato i URL-stien. Vi plukker tittel + dato fra
    hver artikkel-lenke. Default-bydel settes av source['bydel'].
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Frogner"
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        seen = set()
        count = 0
        limit = source.get("limit", 10)
        for url, date_iso, title in _POLITI_ARTICLE_RE.findall(html_txt):
            if url in seen:
                continue
            seen.add(url)
            full_url = "https://www.politiet.no" + url
            title = title.strip().replace("\\", "")
            try:
                matched = S.resolve_text_match_bydel({"title": title, "summary": ""})
            except Exception:
                matched = None
            bydel = matched or bydel_default
            dt = f"{date_iso}T12:00:00+00:00"
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel,
                title=title,
                url=full_url,
                source="Oslo politidistrikt",
                source_id=source["id"],
                published_iso=dt,
                date_iso=date_iso,
                summary="",
                category="sikkerhet",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                break


# --- Ruter avvik via Entur SIRI-SX -----------------------------------------
# Entur aggregerer driftsmeldinger for hele Norge; datasetId=RUT filtrerer til
# Ruter (buss/trikk/T-bane/baat i Oslo + Akershus). XML-format, SIRI-SX-standard.
ET_CLIENT_NAME = "xlent-thomaselboth-bydelsnytt"
_SIRI_NS = {"s": "http://www.siri.org.uk/siri"}


def _fetch_xml(url: str, headers: dict | None = None, timeout: int = 20) -> Optional[bytes]:
    hdr = {"User-Agent": UA, "Accept": "application/xml"}
    if headers:
        hdr.update(headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  [fetcher] WARN: could not fetch {url}: {e}")
        return None


def _sx_text(elem, path: str, lang: str = "NO") -> str:
    """Hent SIRI-SX tekst i foretrukket spraak. Returner tom streng hvis ikke finnes."""
    if elem is None:
        return ""
    # Proev foerst element med xml:lang=lang
    for t in elem.findall(path, _SIRI_NS):
        t_lang = t.get("{http://www.w3.org/XML/1998/namespace}lang") or ""
        if t_lang.upper() == lang.upper() and (t.text or "").strip():
            return (t.text or "").strip()
    # Ellers foerste element med tekst
    for t in elem.findall(path, _SIRI_NS):
        if (t.text or "").strip():
            return (t.text or "").strip()
    return ""


def fetch_from_html_ruter(source: dict) -> Iterable[RawStory]:
    """Hent Ruter driftsmeldinger fra Entur SIRI-SX REST.

    Siden Ruter-siden er en React-app (ingen RSS), bruker vi Entur sitt
    standardiserte datafeed (datasetId=RUT). Vi filtrerer bort stengte
    situasjoner og saker som er utloept, og mapper hver sak til en RawStory
    med kategori=trafikk og bydel fra tittelmatch (ellers default).
    """
    import xml.etree.ElementTree as ET
    fetched_at = datetime.now(timezone.utc).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Frogner"
    limit = source.get("limit", 25)
    headers = {"ET-Client-Name": ET_CLIENT_NAME}
    for url in source.get("urls", []):
        body = _fetch_xml(url, headers=headers)
        if not body:
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            print(f"  [fetcher] WARN: Ruter XML parse feilet: {e}")
            continue
        count = 0
        for pt in root.iter(f"{{{_SIRI_NS['s']}}}PtSituationElement"):
            progress = _sx_text(pt, "s:Progress")
            if progress and progress.lower() in ("closed", "closing"):
                continue
            vp = pt.find("s:ValidityPeriod", _SIRI_NS)
            end_time = _sx_text(vp, "s:EndTime") if vp is not None else ""
            if end_time and end_time < now_iso:
                continue
            start_time = (_sx_text(vp, "s:StartTime") if vp is not None else "") or now_iso
            situation_number = _sx_text(pt, "s:SituationNumber") or _sx_text(pt, "s:SituationRef")
            summary = _sx_text(pt, "s:Summary", "NO")
            description = _sx_text(pt, "s:Description", "NO")
            if not summary:
                continue
            if len(summary) < 10:
                continue
            lines = []
            for ln in pt.iter(f"{{{_SIRI_NS['s']}}}LineRef"):
                txt = (ln.text or "").strip()
                if txt.startswith("RUT:Line:"):
                    lines.append(txt.split(":", 2)[-1])
            if lines:
                lines = sorted(set(lines))[:8]
                summary_full = summary
                if description and description != summary:
                    summary_full = f"{summary} \u2014 {description}"
                summary_out = f"Linjer: {', '.join(lines)}. {summary_full}"
            else:
                summary_out = summary
                if description and description != summary:
                    summary_out = f"{summary} \u2014 {description}"
            sit_id_short = situation_number.split(":")[-1] if situation_number else ""
            full_url = f"https://ruter.no/avvik/?s={sit_id_short}" if sit_id_short else "https://ruter.no/avvik/"
            date_iso = start_time[:10] if len(start_time) >= 10 else now_iso[:10]
            try:
                matched = S.resolve_text_match_bydel({
                    "title": summary,
                    "summary": description,
                })
            except Exception:
                matched = None
            bydel = matched or bydel_default
            yield RawStory(
                id=_make_id(full_url, summary),
                bydel=bydel,
                title=summary[:160],
                url=full_url,
                source="Ruter avvik",
                source_id=source["id"],
                published_iso=start_time,
                date_iso=date_iso,
                summary=summary_out[:600],
                category="trafikk",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                break



# --- OsloMet forskningsnyheter + institusjonelle nyheter ------------------
_OSLOMET_LINK_RE = re.compile(
    r'<a[^>]+href="(/(?:forskning/forskningsnyheter|om/nyheter)/[^"#?]+)"[^>]*>'
    r'([\s\S]{1,600}?)</a>'
)


def fetch_from_html_oslomet(source: dict) -> Iterable[RawStory]:
    """OsloMet /forskning/forskningsnyheter + /om/nyheter.

    Listingen har lenker <a href="/forskning/forskningsnyheter/..."> der
    lenketeksten inneholder bade tittel og et kort ingress. Vi splitter paa
    foerste dobbeltmellomrom/overskrift og bruker resten som summary.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Nordre Aker"
    limit = source.get("limit", 15)
    seen = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        for m in _OSLOMET_LINK_RE.finditer(html_txt):
            href = m.group(1)
            block = m.group(2)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 8:
                continue
            # Del paa foerste punktum for tittel/summary-split
            parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
            title = parts[0][:200].strip()
            summary = parts[1].strip() if len(parts) > 1 else ""
            full_url = "https://www.oslomet.no" + href
            if full_url in seen:
                continue
            seen.add(full_url)
            now_iso = fetched_at
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel_default,
                title=title,
                url=full_url,
                source=source.get("name", "OsloMet"),
                source_id=source["id"],
                published_iso=now_iso,
                date_iso=now_iso[:10],
                summary=summary[:600],
                category="skole",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return


# --- BI Business Review / presserom ---------------------------------------
_BI_LINK_RE = re.compile(
    r'<a[^>]+href="(/forskning/business-review/articles/(\d{4})/(\d{2})/[^"#?]+)"[^>]*>'
    r'([\s\S]{1,600}?)</a>'
)


def fetch_from_html_bi(source: dict) -> Iterable[RawStory]:
    """BI Business Review - forskningsartikler.

    Articles ligger paa /forskning/business-review/articles/YYYY/MM/slug/.
    Dato hentes fra URL-en. Lenketeksten har ofte seksjonsprefiks
    "BI Business Review" som strippes.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Nordre Aker"
    limit = source.get("limit", 15)
    seen = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        for m in _BI_LINK_RE.finditer(html_txt):
            href, yr, mo, block = m.group(1), m.group(2), m.group(3), m.group(4)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            # Strip section-prefix
            text = re.sub(r"^(BI Business Review|BI Presserom)\s+", "", text)
            if len(text) < 8:
                continue
            title = text[:200].strip()
            full_url = "https://www.bi.no" + href
            if full_url in seen:
                continue
            seen.add(full_url)
            date_iso = f"{yr}-{mo}-01"
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel_default,
                title=title,
                url=full_url,
                source=source.get("name", "BI Business Review"),
                source_id=source["id"],
                published_iso=f"{date_iso}T12:00:00+00:00",
                date_iso=date_iso,
                summary="",
                category="naering",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return


# --- Deichman aktuelt ------------------------------------------------------
_DEICHMAN_LINK_RE = re.compile(
    r'<a[^>]+href="(/aktuelt/[^"#?]+)"[^>]*>([\s\S]{1,500}?)</a>'
)


def fetch_from_html_deichman(source: dict) -> Iterable[RawStory]:
    """Deichman /aktuelt - nyheter fra bibliotekene.

    SPA-likt grensesnitt, men listesiden server-renderer artikkel-lenker med
    tittel i klartekst. Dato finnes ikke i URL; vi bruker fetched_at.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Gamle Oslo"
    limit = source.get("limit", 15)
    seen = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        for m in _DEICHMAN_LINK_RE.finditer(html_txt):
            href = m.group(1)
            block = m.group(2)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 5 or "biblioteket" == text.lower():
                continue
            title = text[:200].strip()
            # Avkod %XX i URL for renere link
            try:
                import urllib.parse as up
                href_decoded = up.unquote(href)
            except Exception:
                href_decoded = href
            full_url = "https://www.deichman.no" + href_decoded
            if full_url in seen:
                continue
            seen.add(full_url)
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel_default,
                title=title,
                url=full_url,
                source=source.get("name", "Deichman"),
                source_id=source["id"],
                published_iso=fetched_at,
                date_iso=fetched_at[:10],
                summary="",
                category="kultur",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return


SCRAPERS = {
    "iltry": fetch_from_html_iltry,
    "kondis": fetch_from_html_kondis,
    "politi-oslo": fetch_from_html_politi,
    "ruter-sx": fetch_from_html_ruter,
    "oslomet": fetch_from_html_oslomet,
    "bi": fetch_from_html_bi,
    "deichman": fetch_from_html_deichman,
}


def fetch_from_html(source: dict) -> Iterable[RawStory]:
    scraper = SCRAPERS.get(source.get("scraper"))
    if scraper is None:
        print(f"  [fetcher] WARN: no scraper for {source['id']}")
        return
    yield from scraper(source)


def fetch_all(health_data: dict | None = None) -> list[RawStory]:
    """Hent alle kilder. Hvis health_data gis (dict fra health.load()),
    blir per-kilde-statistikk registrert i den via health.record()."""
    from . import health as H
    out: list[RawStory] = []
    for src in S.RSS_SOURCES:
        print(f"[fetcher] rss {src['id']} -> {src['url']}")
        count = 0
        for story in fetch_from_rss(src):
            out.append(story)
            count += 1
        print(f"[fetcher] rss {src['id']}: {count} saker mappet til bydel")
        if health_data is not None:
            H.record(health_data, src["id"], src.get("name", src["id"]), count)
    for src in getattr(S, "HTML_SOURCES", []):
        print(f"[fetcher] html {src['id']} -> {len(src.get('urls', []))} sider")
        count = 0
        for story in fetch_from_html(src):
            out.append(story)
            count += 1
        print(f"[fetcher] html {src['id']}: {count} saker scrapet")
        if health_data is not None:
            H.record(health_data, src["id"], src.get("name", src["id"]), count)
    return out


if __name__ == "__main__":
    stories = fetch_all()
    print(f"\nTotalt: {len(stories)} saker")
    from collections import Counter
    per_bydel = Counter(s.bydel for s in stories)
    for b, n in sorted(per_bydel.items(), key=lambda x: -x[1]):
        print(f"  {b}: {n}")
