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
