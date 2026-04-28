"""Hent nyhetssaker fra RSS-feeds og HTML-scrapers definert i sources.py."""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    event_date: str = ""  # ISO-timestamp for arrangement (valgfri)

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
            # Filtrer bort saker som ligger utenfor Oslo kommune.
            # Ruter dekker hele Viken — vi vil kun ha Oslo-saker.
            _NON_OSLO_PLACES = (
                "drøbak", "frogn kommune", "ås ", "ås,", "ås.", "ås -",
                "nesodden", "bærum", "asker", "lillestrøm", "lørenskog",
                "skedsmo", "strømmen", "nittedal", "rælingen", "enebakk",
                "ski ", "ski,", "ski.", "nordre follo", "vestby",
                "sørum", "fet", "aurskog", "høland", "nannestad",
                "gjerdrum", "ullensaker", "jessheim", "eidsvoll",
                "nannestad", "hurdal",
            )
            _haystack = f"{summary} {description or ''}".lower()
            if any(p in _haystack for p in _NON_OSLO_PLACES):
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


# --- Vårt Oslo -----------------------------------------------------------
_VARTOSLO_LINK_RE = re.compile(
    r'href="(/[a-z0-9-]+/[a-z0-9-]+/(\d{6,}))"[^>]*>\s*([^<]{15,250})',
    re.I,
)

_VARTOSLO_BYDEL_MAP = {
    "bydel-alna": "Alna",
    "bydel-bjerke": "Bjerke",
    "bydel-frogner": "Frogner",
    "bydel-gamle-oslo": "Gamle Oslo",
    "bydel-grorud": "Grorud",
    "bydel-grunerlokka": "Grünerløkka",
    "bydel-nordre-aker": "Nordre Aker",
    "bydel-nordstrand": "Nordstrand",
    "bydel-sagene": "Sagene",
    "bydel-st-hanshaugen": "St. Hanshaugen",
    "bydel-stovner": "Stovner",
    "bydel-sondre-nordstrand": "Søndre Nordstrand",
    "bydel-ullern": "Ullern",
    "bydel-vestre-aker": "Vestre Aker",
    "bydel-ostensjo": "Østensjø",
}


_VARTOSLO_URL_RE = re.compile(
    r'href="(/([a-z0-9-]+)/([a-z0-9-]+)/(\d{6,}))"', re.I
)
_VARTOSLO_HTAG_RE = re.compile(
    r'<(h[1-6]|span|p)[^>]*>\s*([^<][\s\S]{10,250}?)\s*</\1>'
)


def _slug_to_title(slug: str) -> str:
    """Fallback: omvend kebab-slug til lesbar tittel."""
    words = slug.replace("-", " ").strip()
    return words[:1].upper() + words[1:] if words else ""


def fetch_from_html_vartoslo(source: dict):
    """Vårt Oslo — bydelsavisa for hele Oslo.

    URL-mønster: /tag1-tag2-tag3/slug/{id}. Bydel hentes fra tag-delen hvis
    'bydel-<navn>' finnes, ellers fallback til source['bydel']. Tittel
    plukkes fra nærmeste h-tag etter lenken, eller slug som fallback.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "St. Hanshaugen"
    limit = source.get("limit", 30)
    seen = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        for m in _VARTOSLO_URL_RE.finditer(html_txt):
            href = m.group(1)
            tags_part = m.group(2).lower()
            slug = m.group(3)
            story_id = m.group(4)
            if story_id in seen:
                continue
            seen.add(story_id)

            # Tittel: let etter nærmeste h-tag i ~800 tegn etter lenken
            window = html_txt[m.end():m.end() + 800]
            title = ""
            h = _VARTOSLO_HTAG_RE.search(window)
            if h:
                raw = re.sub(r"<[^>]+>", " ", h.group(2))
                title = re.sub(r"\s+", " ", raw).strip()
            if len(title) < 10:
                title = _slug_to_title(slug)
            if len(title) < 10:
                continue

            # Bydel
            bydel_match = bydel_default
            for key, name in _VARTOSLO_BYDEL_MAP.items():
                if key in tags_part:
                    bydel_match = name
                    break

            full_url = "https://www.vartoslo.no" + href
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel_match,
                title=title,
                url=full_url,
                source=source.get("name", "Vårt Oslo"),
                source_id=source["id"],
                published_iso=fetched_at,
                date_iso=fetched_at[:10],
                summary="",
                category="annet",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return



# --- Bymiljoetaten kunngjoringer (Algolia-API) -----------------------------
_BYM_ALGOLIA_URL = (
    "https://NJ4QX1MFJ2-dsn.algolia.net/1/indexes/prod_oslo_kommune_no_numerical_desc/query"
)
_BYM_ALGOLIA_KEY = "4ce897d2ad7bca6a9fbcac2888b35801"
_BYM_ALGOLIA_APP = "NJ4QX1MFJ2"


def fetch_from_html_bym_kunngjoringer(source: dict):
    """BYM kunngjoeringer via oslo.kommune.no sitt Algolia-soekeindeks.

    Siden er JS-rendret, men Algolia-API er offentlig. Vi spoer etter
    hoeringer, utlysninger og kunngjoeringer knyttet til Bymiljoetaten,
    og bruker text_match mot et par bydelsstikkord for aa plassere saken.
    """
    import json as _json
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Frogner"
    limit = source.get("limit", 20)

    payload = _json.dumps({
        "params": (
            "query=bymiljoetaten&hitsPerPage=30"
            "&filters=meta.type:entry_article_announcement"
        )
    }).encode()
    req = urllib.request.Request(
        _BYM_ALGOLIA_URL,
        data=payload,
        headers={
            "User-Agent": UA,
            "X-Algolia-Api-Key": _BYM_ALGOLIA_KEY,
            "X-Algolia-Application-Id": _BYM_ALGOLIA_APP,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
            data = _json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  [fetcher] WARN: BYM Algolia feilet: {e}")
        return

    count = 0
    for hit in data.get("hits", []):
        meta = hit.get("meta") or {}
        url = (meta.get("url") or "").strip()
        title = (hit.get("name") or "").strip()
        if not url or not title:
            continue

        # Strukturert summary fra editorial_content
        summary = ""
        for ec in hit.get("editorial_content") or []:
            if ec.get("type") == "lead" and ec.get("content"):
                summary = ec["content"].strip()[:400]
                break

        published = (meta.get("published_at") or "").strip()
        if not published:
            published = fetched_at
        date_iso = (published or fetched_at)[:10]

        # Bydel-heuristikk: bruk stroek-tabellen fra sources for full daekning
        haystack = (title + " " + summary).lower()
        bydel = None
        for stroek, b in S.STROEK_TIL_BYDEL.items():
            if stroek in haystack:
                bydel = b
                break
        # Spesialtilfelle: akerselva -> Gruenerloekka
        if bydel is None and "akerselva" in haystack:
            bydel = "Gr\u00fcnerl\u00f8kka"
        if bydel is None:
            # Direkte bydelsnavn i haystack?
            for b in S.BYDELER:
                if b.lower() in haystack:
                    bydel = b
                    break
        if bydel is None:
            bydel = bydel_default

        yield RawStory(
            id=_make_id(url, title),
            bydel=bydel,
            title=title,
            url=url,
            source=source.get("name", "Bymiljoetaten"),
            source_id=source["id"],
            published_iso=published,
            date_iso=date_iso,
            summary=summary,
            category="politikk",
            fetched_at_iso=fetched_at,
        )
        count += 1
        if count >= limit:
            return


# --- Skiforeningen ---------------------------------------------------------
_SKIFORENINGEN_ARTICLE_RE = re.compile(
    r'href="(/nyheter/[a-z0-9-]+/)"[^>]*>\s*([^<]{5,120})</a>',
    re.IGNORECASE,
)


def fetch_from_html_skiforeningen(source: dict):
    """Skiforeningen /nyheter — skraper artikkel-lenker fra oversiktssiden.

    Siden har ingen RSS. Artikkel-lenker foelger moensteret /nyheter/<slug>/.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Vestre Aker"  # Holmenkollen
    limit = source.get("limit", 20)
    seen: set[str] = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        # Finn alle /nyheter/<slug>/-lenker (ekskluder selve oversiktssiden)
        for m in re.finditer(r'href="(/nyheter/[a-z0-9-]+/?)"', html_txt):
            path = m.group(1)
            if path in seen or path.rstrip("/") == "/nyheter":
                continue
            seen.add(path)

            # Tittel: slug -> Title Case
            slug = path.strip("/").split("/")[-1]
            title = slug.replace("-", " ").strip().capitalize()
            if len(title) < 5:
                continue

            full_url = "https://www.skiforeningen.no" + path
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel_default,
                title=title,
                url=full_url,
                source=source.get("name", "Skiforeningen"),
                source_id=source["id"],
                published_iso=fetched_at,
                date_iso=fetched_at[:10],
                summary="",
                category="idrett",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return


# --- Akersposten (Oslo vest: Vestre Aker, Ullern, Frogner) -----------------
_AKERSPOSTEN_URL_RE = re.compile(
    r'href="(?://www\.akersposten\.no)?(/([a-z0-9-]+)/s/5-\d+-(\d+))"',
    re.IGNORECASE,
)

# Strok/omraade -> bydel. Lengst forst for aa unngaa prefix-match.
_AKERSPOSTEN_STROEK = [
    ("vinderen", "Vestre Aker"),
    ("holmenkollen", "Vestre Aker"),
    ("diakonhjemmet", "Vestre Aker"),
    ("sorkedalen", "Vestre Aker"),
    ("soerkedalen", "Vestre Aker"),
    ("slemdal", "Vestre Aker"),
    ("smestad", "Vestre Aker"),
    ("roa", "Vestre Aker"),
    ("hovseter", "Vestre Aker"),
    ("voksenkollen", "Vestre Aker"),
    ("ris", "Vestre Aker"),
    ("gaustad", "Vestre Aker"),
    ("sognsvann", "Vestre Aker"),
    ("ullern", "Ullern"),
    ("skoyen", "Ullern"),
    ("skoeyen", "Ullern"),
    ("bestum", "Ullern"),
    ("lilleaker", "Ullern"),
    ("montebello", "Ullern"),
    ("sollerud", "Ullern"),
    ("bygdoy", "Frogner"),
    ("bygdoey", "Frogner"),
    ("frogner", "Frogner"),
    ("majorstu", "Frogner"),
    ("skillebekk", "Frogner"),
    ("sogn", "Nordre Aker"),
    ("nordberg", "Nordre Aker"),
    ("tasen", "Nordre Aker"),
]


def _akersposten_bydel_from_text(text: str, default: str) -> str:
    t = text.lower()
    for needle, bydel in _AKERSPOSTEN_STROEK:
        if needle in t:
            return bydel
    return default


def fetch_from_html_akersposten(source: dict):
    """Akersposten - lokalavis for Oslo vest.

    Artikkel-URL-moenster: /<slug>/s/5-<sec>-<id>. Bydel bestemmes av
    stroek-navn i slug; default faller til Vestre Aker (dekningens tyngdepunkt).
    Mange saker er paywalled, men vi lenker videre uansett.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    bydel_default = source.get("bydel") or "Vestre Aker"
    limit = source.get("limit", 20)
    seen: set[str] = set()
    count = 0
    for list_url in source.get("urls", []):
        html_txt = _fetch_html(list_url)
        if not html_txt:
            continue
        for m in _AKERSPOSTEN_URL_RE.finditer(html_txt):
            path = m.group(1)
            slug = m.group(2)
            story_id = m.group(3)
            if story_id in seen:
                continue
            seen.add(story_id)

            title = _slug_to_title(slug)
            if len(title) < 10:
                continue

            bydel = _akersposten_bydel_from_text(slug, bydel_default)
            full_url = "https://www.akersposten.no" + path
            yield RawStory(
                id=_make_id(full_url, title),
                bydel=bydel,
                title=title,
                url=full_url,
                source=source.get("name", "Akersposten"),
                source_id=source["id"],
                published_iso=fetched_at,
                date_iso=fetched_at[:10],
                summary="",
                category="annet",
                fetched_at_iso=fetched_at,
            )
            count += 1
            if count >= limit:
                return


def fetch_from_html_kjelsaas(source: dict) -> Iterable[RawStory]:
    """Scrape Kjelsaas IL — custom blog-CMS via /next/blog/post/."""
    import re, urllib.parse, html as _html
    base = source["urls"][0]
    body = _fetch_html(base)
    if not body:
        return
    # Click-URLer paa formen /next/blog/click?id=NN&url=ENCODED_POST_URL
    clicks = re.findall(
        r'/next/blog/click\?id=\d+(?:&amp;|&)url=([^"\']+)', body
    )
    seen: set[str] = set()
    posts: list[str] = []
    for raw in clicks:
        decoded = urllib.parse.unquote(raw.replace('&amp;', '&'))
        m = re.search(r'/next/blog/post/(\d+)/([\w\-]+)', decoded)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen:
            continue
        seen.add(pid)
        full_url = 'https://www.kjelsaas.no/next/blog/post/' + pid + '/' + m.group(2)
        posts.append(full_url)
    limit = source.get("limit", 12)
    posts = posts[:limit]
    bydel = source.get("bydel", "Nordre Aker")
    for url in posts:
        page = _fetch_html(url)
        if not page:
            continue
        def _meta(prop: str) -> str:
            mm = re.search(
                r'<meta\s+(?:name|property)="' + re.escape(prop)
                + r'"\s+content="([^"]*)"', page
            )
            return _html.unescape(mm.group(1)).strip() if mm else ""
        title = _meta("og:title") or _meta("twitter:title")
        if not title:
            t = re.search(r'<title[^>]*>([^<]+)</title>', page)
            title = _html.unescape(t.group(1)).strip() if t else ""
        if not title:
            continue
        summary = _clean_summary(_meta("og:description") or _meta("description"))
        image = _meta("og:image")
        # Dato: Kjelsaas eksponerer ikke pubDate. Bruk image-URL-mønstret
        # /froala/.../YYYY/M/D/... naar tilgjengelig, ellers tom string.
        date_iso = ""
        if image:
            mm = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', image)
            if mm:
                yy, mo, dd = mm.group(1), mm.group(2).zfill(2), mm.group(3).zfill(2)
                date_iso = yy + '-' + mo + '-' + dd
        yield RawStory(
            id=_make_id(url, title),
            bydel=bydel,
            title=title,
            url=url,
            source=source.get("name", source["id"]),
            source_id=source["id"],
            published_iso=date_iso,
            date_iso=date_iso,
            summary=summary,
        )


# --- Furuset IF -------------------------------------------------------------
# www.furuset.no har kun /b/<slug>-artikler uten RSS. Forsiden lister tittel +
# subtitle direkte i HTML; detaljside har og:title og og:description.

def fetch_from_html_furuset(source: dict) -> Iterable[RawStory]:
    """Furuset IF — scraper /b/<slug>-artikler."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    today_iso = datetime.now(timezone.utc).date().isoformat()
    list_url = (source.get("urls") or ["https://www.furuset.no/"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    # Finner /b/<slug>-lenker med tittel
    paths = sorted(set(re.findall(r'<a href="(/b/[a-z0-9-]+)"', body)))
    seen: set[str] = set()
    count = 0
    limit = source.get("limit", 15)
    for path in paths:
        if count >= limit or path in seen:
            continue
        seen.add(path)
        url = f"https://www.furuset.no{path}"
        detail = _fetch_html(url)
        if not detail:
            continue
        og_t = re.search(
            r'<meta property="og:title" content="([^"]+)"', detail,
        )
        og_d = re.search(
            r'<meta property="og:description" content="([^"]+)"', detail,
        )
        title = og_t.group(1).strip() if og_t else ""
        if not title:
            continue
        from html import unescape as _unesc
        title = _unesc(title)
        desc = _unesc(og_d.group(1)) if og_d else ""
        yield RawStory(
            id=_make_id(url, title),
            bydel="Alna",
            title=title,
            url=url,
            source="Furuset IF",
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=today_iso,
            summary=desc[:500],
            category="idrett",
        )
        count += 1


# --- Kulturkirken Jakob — konserter -----------------------------------------
# kulturkirken.no/program lister event-lenker som peker til jakob.no/program/<slug>.
# Hver detaljside har og:title og norske datoer ("17. desember 2026").

def fetch_from_html_jakob(source: dict) -> Iterable[RawStory]:
    """Kulturkirken Jakob konserter."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc)
    list_url = (source.get("urls") or
                ["https://kulturkirken.no/program"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    urls = sorted(set(re.findall(
        r'href="(https://www\.jakob\.no/program/[a-z0-9-]+)"', body
    )))
    seen: set[str] = set()
    count = 0
    limit = source.get("limit", 12)
    for url in urls:
        if count >= limit or url in seen:
            continue
        seen.add(url)
        detail = _fetch_html(url)
        if not detail:
            continue
        og_t = re.search(
            r'<meta property="og:title" content="([^"]+)"', detail,
        )
        og_i = re.search(
            r'<meta property="og:image" content="([^"]+)"', detail,
        )
        title = og_t.group(1).strip() if og_t else ""
        if not title:
            continue
        from html import unescape as _unesc
        title = _unesc(title)
        # Foerste fremtidige dato
        first_date = ""
        candidates = []
        from datetime import date as _date
        _MND = {"jan":"01","feb":"02","mar":"03","apr":"04","mai":"05",
                "jun":"06","jul":"07","aug":"08","sep":"09","okt":"10",
                "nov":"11","des":"12","januar":"01","februar":"02","mars":"03",
                "april":"04","juni":"06","juli":"07","august":"08",
                "september":"09","oktober":"10","november":"11","desember":"12"}
        for m in re.finditer(
            r"\b(\d{1,2})\.\s*(jan|feb|mar|apr|mai|jun|jul|aug|sep|okt|nov|des|"
            r"januar|februar|mars|april|juni|juli|august|september|oktober|"
            r"november|desember)\.?\s*(\d{4})?", detail, re.IGNORECASE,
        ):
            try:
                day = int(m.group(1))
                mon = int(_MND[m.group(2).lower()])
                year = int(m.group(3)) if m.group(3) else today.year
                if year < today.year: year = today.year + 1
                d = _date(year, mon, day)
                if d >= today.date():
                    candidates.append(d)
            except (KeyError, ValueError):
                pass
        if candidates:
            first_date = min(candidates).isoformat()
        date_iso = first_date or today.date().isoformat()
        yield RawStory(
            id=_make_id(url, title),
            bydel="St. Hanshaugen",  # Hausmannsgate
            title=title,
            url=url,
            source="Kulturkirken Jakob",
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=date_iso,
            summary=f"Konsert/arrangement i Kulturkirken Jakob. {title[:200]}",
            category="kultur",
            event_date=first_date,
        )
        count += 1


# --- Nationaltheatret — forestillinger ------------------------------------
# nationaltheatret.no/forestillinger/ er en Next.js-side med 22 forestillings-
# lenker. Hver detaljside har <title>"<Tittel> | Nationaltheatret"</title>,
# <h1> med samme tittel og inline norske datoer ("27. september 2026").
# Tittel hentes fra <h1>; foerste fremtidige dato fra teksten.

_NATIONAL_MONTH_FULL = {
    "januar": "01", "februar": "02", "mars": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "desember": "12",
}


def _national_first_date(html: str, current_year: int) -> str:
    """Foerste dato >= i dag i ISO-format. Aksepterer 'dd. mai 2026' og kort."""
    today = datetime.now(timezone.utc).date()
    candidates = []
    pat = (r"\b(\d{1,2})\.\s*(januar|februar|mars|april|mai|juni|juli|august|"
           r"september|oktober|november|desember)\.?\s*(\d{4})?")
    for m in re.finditer(pat, html, re.IGNORECASE):
        day = int(m.group(1))
        mon = _NATIONAL_MONTH_FULL[m.group(2).lower()]
        year = int(m.group(3)) if m.group(3) else current_year
        if year < current_year:
            year = current_year + 1
        try:
            from datetime import date as _date
            d = _date(year, int(mon), day)
            if d >= today:
                candidates.append(d)
        except ValueError:
            continue
    return min(candidates).isoformat() if candidates else ""


def fetch_from_html_nationaltheatret(source: dict) -> Iterable[RawStory]:
    """Nationaltheatret forestillinger."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc)
    list_url = (source.get("urls") or
                ["https://www.nationaltheatret.no/forestillinger/"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    paths = sorted(set(re.findall(
        r'href="(/forestillinger/[a-z0-9-]+)"', body
    )))
    seen: set[str] = set()
    count = 0
    limit = source.get("limit", 12)
    for path in paths:
        if count >= limit:
            break
        if path in seen:
            continue
        seen.add(path)
        full_url = f"https://www.nationaltheatret.no{path}"
        detail = _fetch_html(full_url)
        if not detail:
            continue
        # Tittel: <h1> eller <title>-prefix foer " | Nationaltheatret"
        m_h1 = re.search(r'<h1[^>]*>(.*?)</h1>', detail, re.DOTALL)
        title = ""
        if m_h1:
            title = re.sub(r'<[^>]+>', '', m_h1.group(1)).strip()
        if not title:
            mt = re.search(r'<title[^>]*>([^<|]+)', detail)
            if mt:
                title = mt.group(1).strip()
        if not title:
            continue
        first_date = _national_first_date(detail, today.year)
        date_iso = first_date or today.date().isoformat()
        # Description: meta-description som fallback (kan vaere tom for SPA)
        desc = ""
        md = re.search(r'<meta name="description" content="([^"]+)"', detail)
        if md:
            from html import unescape as _unesc
            desc = _unesc(md.group(1))
        yield RawStory(
            id=_make_id(full_url, title),
            bydel="St. Hanshaugen",  # Stortingsgata 15, naermest St. Hanshaugen
            title=title,
            url=full_url,
            source="Nationaltheatret",
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=date_iso,
            summary=desc[:500],
            category="kultur",
            event_date=first_date,
        )
        count += 1


# --- Operaen.no — forestillinger og konserter -----------------------------
# Den Norske Opera & Ballett: scrape /forestillinger/ for produksjons-lenker,
# fetch hver detaljside for tittel, beskrivelse, bilde og foerste forestillings-
# dato. Bydel = Gamle Oslo (Bjorvika).

_OPERAEN_MONTH = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "mai": "05",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09", "okt": "10",
    "nov": "11", "des": "12",
}


def _operaen_first_date(html: str, current_year: int) -> str:
    """Returner foerste fremtidige dato i ISO-format (YYYY-MM-DD)."""
    today = datetime.now(timezone.utc).date()
    candidates = []
    for m in re.finditer(
        r"\b(\d{1,2})\.\s*(jan|feb|mar|apr|mai|jun|jul|aug|sep|okt|nov|des)"
        r"\w*\s*(\d{4})?", html, re.IGNORECASE,
    ):
        day = int(m.group(1))
        mon = _OPERAEN_MONTH[m.group(2).lower()[:3]]
        year = int(m.group(3)) if m.group(3) else current_year
        if year < current_year:
            year = current_year + 1
        try:
            from datetime import date as _date
            d = _date(year, int(mon), day)
            if d >= today:
                candidates.append(d)
        except ValueError:
            continue
    if not candidates:
        return ""
    return min(candidates).isoformat()


def fetch_from_html_operaen(source: dict) -> Iterable[RawStory]:
    """Operaen forestillinger — fetch list, then each detail page."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc)
    list_url = (source.get("urls") or
                ["https://operaen.no/forestillinger/"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    paths = sorted(set(re.findall(
        r'href="(/forestillinger/[a-z0-9-]+/?)"', body
    )))
    seen: set[str] = set()
    count = 0
    limit = source.get("limit", 12)
    for path in paths:
        if count >= limit:
            break
        if path in seen:
            continue
        seen.add(path)
        if "sesonglansering" in path:
            continue  # info-side, ikke forestilling
        full_url = f"https://operaen.no{path}"
        detail = _fetch_html(full_url)
        if not detail:
            continue
        og_title = re.search(
            r'<meta property="og:title" content="([^"]+)"', detail,
        )
        og_desc = re.search(
            r'<meta property="og:description" content="([^"]+)"', detail,
        )
        og_image = re.search(
            r'<meta property="og:image" content="([^"]+)"', detail,
        )
        title = og_title.group(1).strip() if og_title else ""
        if not title:
            continue
        from html import unescape as _unesc
        title = _unesc(title)
        desc = _unesc(og_desc.group(1)) if og_desc else ""
        image = (og_image.group(1) if og_image else "").strip()
        if image and not image.startswith("http"):
            image = f"https://operaen.no{image}"
        first_date = _operaen_first_date(detail, today.year)
        date_iso = first_date or today.date().isoformat()
        # Kategori basert paa tittel
        cat = "kultur"
        title_low = title.lower()
        if "ballett" in title_low or "ballet" in title_low:
            cat = "kultur"
        story = RawStory(
            id=_make_id(full_url, title),
            bydel="Gamle Oslo",  # Operaen i Bjorvika
            title=title,
            url=full_url,
            source="Operaen",
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=date_iso,
            summary=desc[:500],
            category=cat,
            event_date=first_date,
        )
        yield story
        count += 1


# --- Skiforbundet terminliste (Oslo Skikrets) -----------------------------
# skiforbundet.no/terminliste/ har en embedded "events" JSON-blob i HTML-en
# med startDate, eventName, arrangingOrgName, activityName, countyName og
# eventUrl. Vi henter alle og filtrerer paa countyName = "Oslo Skikrets"
# (som geografisk dekker Oslo + omegn).

_SKIFORBUNDET_VENUE_TO_BYDEL = {
    "holmenkollen": "Vestre Aker",
    "tryvann": "Vestre Aker",
    "wyller": "Vestre Aker",
    "frognerseteren": "Vestre Aker",
    "linderud": "Bjerke",
    "linderudkollen": "Bjerke",
    "grefsenkollen": "Nordre Aker",
    "kjelsås": "Nordre Aker",
    "kjelsaas": "Nordre Aker",
    "lillomarka": "Bjerke",
    "kirkerud": "Vestre Aker",
    "rommen": "Stovner",
    "voldsløkka": "Sagene",
    "voldslokka": "Sagene",
    "sagene": "Sagene",
    "skullerud": "Østensjø",
    "manglerud": "Østensjø",
    "ekeberg": "Nordstrand",
}


def _skiforbundet_bydel(event_name: str, org_name: str) -> str:
    text = (event_name + " " + org_name).lower()
    for key, bydel in sorted(
        _SKIFORBUNDET_VENUE_TO_BYDEL.items(), key=lambda kv: -len(kv[0])
    ):
        if key in text:
            return bydel
    # Default: Vestre Aker (Holmenkollen-tyngde i Oslo Skikrets)
    return "Vestre Aker"


def _parse_dmy(date_str: str) -> str:
    """24.04.2026 -> 2026-04-24."""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", date_str or "")
    if not m:
        return ""
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def fetch_from_html_skiforbundet(source: dict) -> Iterable[RawStory]:
    """Skirenn fra skiforbundet.no/terminliste/ filtrert til Oslo Skikrets."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    list_url = (source.get("urls") or
                ["https://www.skiforbundet.no/terminliste/"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    m = re.search(r'"events":(\[.*?\])\s*[,}]', body, re.DOTALL)
    if not m:
        print("  [skiforbundet] kunne ikke finne events-array")
        return
    try:
        events = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f"  [skiforbundet] JSON parse: {e}")
        return
    target_krets = source.get("krets", "Oslo Skikrets")
    count = 0
    for ev in events:
        if ev.get("countyName") != target_krets:
            continue
        name = (ev.get("eventName") or "").strip()
        org = (ev.get("arrangingOrgName") or "").strip()
        url = (ev.get("eventUrl") or "").strip()
        activity = (ev.get("activityName") or "").strip()
        start = _parse_dmy(ev.get("startDate"))
        if not name or not url or not start:
            continue
        bydel = _skiforbundet_bydel(name, org)
        title = f"{name}" + (f" ({activity})" if activity else "")
        summary = (
            f"Skirenn {start}. Arrangoer: {org}. "
            f"Aktivitet: {activity}. Krets: {target_krets}."
        )
        yield RawStory(
            id=_make_id(url, title),
            bydel=bydel,
            title=title,
            url=url,
            source=source.get("name", "Skiforbundet"),
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=start,
            summary=summary,
            category="idrett",
            event_date=start,
        )
        count += 1


# --- Meetup Oslo scraper ---------------------------------------------------
_MEETUP_VENUE_TO_BYDEL = {
    "rebel": "St. Hanshaugen",
    "capra": "Sentrum / Frogner",
    "knowit": "Sagene",
    "schibsted": "Sentrum / Frogner",
    "dnb": "Gamle Oslo",
    "nav": "Sagene",
    "spaces": "Frogner",
    "mesh": "Sentrum / Frogner",
    "epicenter": "Sentrum / Frogner",
    "sannergata": "Sagene",
    "kongens gate": "Gamle Oslo",
    "tjuvholmen": "Frogner",
    "aker brygge": "Frogner",
    "bjorvika": "Gamle Oslo",
    "tøyen": "Gamle Oslo",
    "toyen": "Gamle Oslo",
    "grunerlokka": "Grünerløkka",
}


def _meetup_bydel(venue_name: str, address: str = "") -> str:
    text = f"{venue_name} {address}".lower()
    for key, bydel in sorted(
        _MEETUP_VENUE_TO_BYDEL.items(), key=lambda kv: -len(kv[0])
    ):
        if key in text:
            if bydel.startswith("Sentrum"):
                return "Frogner"
            return bydel
    return "Frogner"


def fetch_from_html_meetup_oslo(source: dict) -> Iterable[RawStory]:
    """Meetup Oslo find-side. Henter inntil source['limit'] events."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    limit = source.get("limit", 15)
    list_url = (source.get("urls") or
                ["https://www.meetup.com/find/?location=no--Oslo&source=EVENTS"])[0]
    body = _fetch_html(list_url)
    if not body:
        return
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        body, re.DOTALL,
    )
    if not m:
        return
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return

    def find_events(obj):
        if isinstance(obj, dict):
            if "title" in obj and "eventUrl" in obj and "dateTime" in obj:
                yield obj
            for v in obj.values():
                yield from find_events(v)
        elif isinstance(obj, list):
            for x in obj:
                yield from find_events(x)

    seen: set[str] = set()
    count = 0
    for ev in find_events(data):
        if count >= limit:
            break
        url = ev.get("eventUrl") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        title = (ev.get("title") or "").strip()
        if not title:
            continue
        venue = ev.get("venue") or {}
        venue_name = ""
        if isinstance(venue, dict):
            venue_name = (venue.get("name") or "").strip()
        if venue_name.lower() in ("online event", "online", "virtual"):
            continue
        when_iso = ev.get("dateTime") or ""
        event_date = when_iso[:10] if when_iso else ""
        date_iso = event_date or fetched_at[:10]
        bydel = _meetup_bydel(venue_name)
        summary_parts = []
        if event_date:
            summary_parts.append(f"Arrangement {event_date}")
        if venue_name:
            summary_parts.append(f"hos {venue_name}")
        desc = (ev.get("description") or "").strip()
        if desc:
            summary_parts.append(desc[:300])
        summary = ". ".join(summary_parts)
        yield RawStory(
            id=_make_id(url, title),
            bydel=bydel,
            title=title,
            url=url,
            source=source.get("name", "Meetup Oslo"),
            source_id=source["id"],
            published_iso=fetched_at,
            date_iso=date_iso,
            summary=summary,
            category="arrangement",
            event_date=event_date or "",
        )
        count += 1


SCRAPERS = {
    "iltry": fetch_from_html_iltry,
    "kondis": fetch_from_html_kondis,
    "politi-oslo": fetch_from_html_politi,
    "ruter-sx": fetch_from_html_ruter,
    "oslomet": fetch_from_html_oslomet,
    "bi": fetch_from_html_bi,
    "deichman": fetch_from_html_deichman,
    "vartoslo": fetch_from_html_vartoslo,
    "bym-kunngjoringer": fetch_from_html_bym_kunngjoringer,
    "skiforeningen": fetch_from_html_skiforeningen,
    "akersposten": fetch_from_html_akersposten,
    "kjelsaas": fetch_from_html_kjelsaas,
    "skiforbundet-terminliste": fetch_from_html_skiforbundet,
    "meetup-oslo": fetch_from_html_meetup_oslo,
    "operaen": fetch_from_html_operaen,
    "nationaltheatret": fetch_from_html_nationaltheatret,
    "jakob": fetch_from_html_jakob,
    "furuset": fetch_from_html_furuset,
}


def fetch_from_html(source: dict) -> Iterable[RawStory]:
    scraper = SCRAPERS.get(source.get("scraper"))
    if scraper is None:
        print(f"  [fetcher] WARN: no scraper for {source['id']}")
        return
    yield from scraper(source)


def _fetch_one_rss(src: dict) -> tuple[dict, list[RawStory]]:
    try:
        return (src, list(fetch_from_rss(src)))
    except Exception as e:
        print(f"  [fetcher] rss {src['id']}: {type(e).__name__}: {e}")
        return (src, [])


def _fetch_one_html(src: dict) -> tuple[dict, list[RawStory]]:
    try:
        return (src, list(fetch_from_html(src)))
    except Exception as e:
        print(f"  [fetcher] html {src['id']}: {type(e).__name__}: {e}")
        return (src, [])


def fetch_all(health_data: dict | None = None,
              max_workers: int = 8) -> Iterable[RawStory]:
    from . import health as H
    rss_sources = [s for s in S.RSS_SOURCES]
    html_sources = [s for s in getattr(S, "HTML_SOURCES", [])]
    out: list[RawStory] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        rss_futs = {pool.submit(_fetch_one_rss, s): s for s in rss_sources}
        html_futs = {pool.submit(_fetch_one_html, s): s for s in html_sources}
        for fut in as_completed(list(rss_futs) + list(html_futs)):
            src, stories = fut.result()
            count = len(stories)
            kind = "rss" if src in rss_sources else "html"
            if kind == "rss":
                print(f"[fetcher] rss {src['id']}: {count} saker mappet til bydel")
            else:
                print(f"[fetcher] html {src['id']}: {count} saker scrapet")
            out.extend(stories)
            if health_data is not None:
                H.record(health_data, src["id"], src.get("name", src["id"]), count)
    return out
