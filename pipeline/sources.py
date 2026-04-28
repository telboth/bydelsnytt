"""Kildeliste for Bydelsnytt Oslo.

Hver kilde angir en URL + en maate aa mappe ferdige entries til en bydel.
"""

BYDELER = [
    "Alna", "Bjerke", "Frogner", "Gamle Oslo", "Grorud", "Gr\u00fcnerl\u00f8kka",
    "Nordre Aker", "Nordstrand", "Sagene", "St. Hanshaugen", "Stovner",
    "S\u00f8ndre Nordstrand", "Ullern", "Vestre Aker", "\u00d8stensj\u00f8",
]


# Stroek / stedsnavn -> bydel. Brukt av text_match_bydel-resolveren for
# feeds som ikke tagger saker per bydel (NRK Oslo og Viken, lokale aviser).
# Rekkefoelge: mer spesifikke navn foer generelle. Substring-match.
STROEK_TIL_BYDEL = {
    # Alna
    "furuset": "Alna", "ellingsrud": "Alna", "lindeberg": "Alna",
    "teisen": "Alna", "hellerud": "Alna", "trosterud": "Alna",
    "tveita": "Alna", "haugerud": "Alna",
    # Bjerke
    "\u00f8kern": "Bjerke", "l\u00f8ren": "Bjerke", "\u00e5rvoll": "Bjerke",
    "linderud": "Bjerke", "sinsen": "Bjerke", "refstad": "Bjerke",
    "veitvet": "Bjerke", "tonsenhagen": "Bjerke",
    # Frogner
    "majorstua": "Frogner", "majorstuen": "Frogner",
    "bygd\u00f8y": "Frogner", "skillebekk": "Frogner",
    "elisenberg": "Frogner", "uranienborg": "Frogner",
    "aker brygge": "Frogner", "tjuvholmen": "Frogner",
    "filipstad": "Frogner", "frognerparken": "Frogner",
    # Gamle Oslo
    "t\u00f8yen": "Gamle Oslo", "gr\u00f8nland": "Gamle Oslo",
    "kampen": "Gamle Oslo", "v\u00e5lerenga": "Gamle Oslo",
    "ensj\u00f8": "Gamle Oslo", "s\u00f8renga": "Gamle Oslo",
    "bj\u00f8rvika": "Gamle Oslo", "etterstad": "Gamle Oslo",
    "gamlebyen": "Gamle Oslo", "lodalen": "Gamle Oslo",
    # Grorud
    "ammerud": "Grorud", "roms\u00e5s": "Grorud",
    "r\u00f8dtvet": "Grorud", "kalbakken": "Grorud",
    # Gruenerloekka
    "gr\u00fcnerl\u00f8kka": "Gr\u00fcnerl\u00f8kka",
    "grunerl\u00f8kka": "Gr\u00fcnerl\u00f8kka",
    "sofienberg": "Gr\u00fcnerl\u00f8kka", "rodel\u00f8kka": "Gr\u00fcnerl\u00f8kka",
    "hasle": "Gr\u00fcnerl\u00f8kka", "d\u00e6lenenga": "Gr\u00fcnerl\u00f8kka",
    "carl berner": "Gr\u00fcnerl\u00f8kka",
    # Nordre Aker
    "nydalen": "Nordre Aker", "sogn": "Nordre Aker",
    "t\u00e5sen": "Nordre Aker", "berg": "Nordre Aker",
    "ullev\u00e5l": "Nordre Aker", "kringsj\u00e5": "Nordre Aker",
    "grefsen": "Nordre Aker", "kjels\u00e5s": "Nordre Aker",
    "sognsvann": "Nordre Aker",
    # Nordstrand
    "bekkelaget": "Nordstrand", "ekeberg": "Nordstrand",
    "ljan": "Nordstrand", "lambertseter": "Nordstrand",
    # Sagene
    "sagene": "Sagene", "bj\u00f8lsen": "Sagene",
    "torshov": "Sagene", "sandaker": "Sagene",
    "iladalen": "Sagene", "voldsl\u00f8kka": "Sagene",
    # St. Hanshaugen
    "st. hanshaugen": "St. Hanshaugen", "st hanshaugen": "St. Hanshaugen",
    "hanshaugen": "St. Hanshaugen", "ila": "St. Hanshaugen",
    "adamstuen": "St. Hanshaugen", "bislett": "St. Hanshaugen",
    # Stovner
    "vestli": "Stovner", "h\u00f8ybr\u00e5ten": "Stovner",
    "fossum": "Stovner", "haugenstua": "Stovner",
    # Soendre Nordstrand
    "holmlia": "S\u00f8ndre Nordstrand", "bj\u00f8rndal": "S\u00f8ndre Nordstrand",
    "mortensrud": "S\u00f8ndre Nordstrand", "prinsdal": "S\u00f8ndre Nordstrand",
    "hauketo": "S\u00f8ndre Nordstrand",
    # Ullern
    "sk\u00f8yen": "Ullern", "bestum": "Ullern", "lilleaker": "Ullern",
    # Vestre Aker
    "holmenkollen": "Vestre Aker", "slemdal": "Vestre Aker",
    "vinderen": "Vestre Aker", "ris": "Vestre Aker",
    "tryvann": "Vestre Aker", "frognerseteren": "Vestre Aker",
    "voksen": "Vestre Aker", "hovseter": "Vestre Aker",
    "huseby": "Vestre Aker", "bogstad": "Vestre Aker",
    "r\u00f8a": "Vestre Aker",
    # Oestensjoe
    "\u00f8stensj\u00f8": "\u00d8stensj\u00f8", "manglerud": "\u00d8stensj\u00f8",
    "abilds\u00f8": "\u00d8stensj\u00f8", "oppsal": "\u00d8stensj\u00f8",
    "b\u00f8ler": "\u00d8stensj\u00f8", "h\u00f8yenhall": "\u00d8stensj\u00f8",
    "bryn": "\u00d8stensj\u00f8",
}


RSS_SOURCES = [
    {
        "id": "oslo-kommune-aktuelt",
        "url": "https://aktuelt.oslo.kommune.no/rss/",
        "weight": 1.0,
        "resolver": "oslo_kommune_tags",
    },
    {
        "id": "groruddalen",
        "url": "https://groruddalen.no/feed",
        "weight": 0.8,
        "resolver": "groruddalen",
    },
    {
        "id": "nrk-oslo-viken",
        "url": "https://www.nrk.no/osloogviken/toppsaker.rss",
        "weight": 0.4,
        "resolver": "text_match_bydel",
    },
    {
        "id": "skeid",
        "name": "Skeid",
        "url": "https://www.skeid.no/rss-nyheter",
        "bydel": "Nordre Aker",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "vif-fotball",
        "name": "V\u00e5lerenga Fotball",
        "url": "https://www.vif-fotball.no/rss-nyheter",
        "bydel": "Gamle Oslo",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "boeler-if",
        "name": "B\u00f8ler IF",
        "url": "https://bolerif.no/feed/",
        "bydel": "\u00d8stensj\u00f8",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "grorud-il",
        "name": "Grorud IL",
        "url": "https://www.grorud-il.no/rss-nyheter",
        "bydel": "Grorud",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "vif",
        "name": "V\u00e5lerenga (klubben)",
        "url": "https://vif.no/feed/",
        "bydel": "Gamle Oslo",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "ready",
        "name": "Ready (tennis/curling)",
        "url": "https://ready.no/feed/",
        "bydel": "Vestre Aker",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "klemetsrud",
        "name": "Klemetsrud IL",
        "url": "https://www.klemetsrudil.no/feed/",
        "bydel": "S\u00f8ndre Nordstrand",
        "weight": 0.6,
        "resolver": "fixed_bydel",
    },
    {
        # Oslo Kajakklubb \u2014 flattvann/havpadling/surfski. Klubbhus paa Bestum.
        "id": "okk",
        "name": "Oslo Kajakklubb",
        "url": "https://www.okk.org/feed/",
        "bydel": "Ullern",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        # loppemarkeder.com \u2014 kuratert oversikt over alle FAU-loppiser i
        # Oslo. RSS gir 20 forste, hver med skole-navn i tittel som vi
        # mapper til bydel via text_match_bydel.
        "id": "loppemarkeder",
        "name": "Loppemarkeder i Oslo",
        "url": "https://www.loppemarkeder.com/feed/",
        "bydel": "Frogner",  # fallback hvis strok ikke matcher
        "weight": 0.5,
        "resolver": "text_match_bydel",
    },
    {
        "id": "sageneif",
        "name": "Sagene IF",
        "url": "https://sageneif.no/rss-feed",
        "bydel": "Sagene",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "heming",
        "name": "Heming",
        "url": "https://www.heming.no/feed/",
        "bydel": "Vestre Aker",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "lyn1896",
        "name": "Lyn Fotball",
        "url": "https://www.lyn1896.no/rss-nyheter",
        "bydel": "Nordre Aker",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "skeid",
        "name": "Skeid",
        "url": "https://www.skeid.no/rss-nyheter",
        "bydel": "Sagene",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "ltsk",
        "name": "Lille T\u00f8yen SK",
        "url": "https://ltsk.no/wp/feed/",
        "bydel": "Gamle Oslo",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "ofa",
        "name": "OFA — Oslomarkas Fiskeadministrasjon",
        "url": "https://ofa.no/feed/",
        "bydel": "Marka",
        "weight": 0.4,
        "resolver": "fixed_bydel",
    },
    {
        "id": "lyn",
        "name": "Lyn (lyn.no)",
        "url": "https://www.lyn.no/nyheter?format=rss",
        "bydel": "Nordre Aker",  # Ullevaal stadion / Sognsvann
        "weight": 0.4,
        "resolver": "fixed_bydel",
    },
    {
        "id": "heming",
        "name": "Heming",
        "url": "https://www.heming.no/feed/",
        "bydel": "Vestre Aker",  # anlegg ved Holmenkollen/Slemdal
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "oppsal-handball",
        "name": "Oppsal H\u00e5ndball",
        "url": "https://www.oppsalhandball.no/feed/",
        "bydel": "\u00d8stensj\u00f8",
        "weight": 0.5,
        "resolver": "fixed_bydel",
    },
    {
        "id": "vegvesen",
        "name": "Statens vegvesen",
        "url": "https://www.vegvesen.no/om-oss/presse/aktuelt/rss/",
        "bydel": "Frogner",
        "weight": 0.4,
        "resolver": "text_match_bydel_fallback",
    },
    # E24 fjernet 24.04.2026: RSS-feeden har bare 4 siste saker og naesten
    # ingen nevner Oslo — ga bare frustrasjon i source-health-banneret.
    {
        "id": "tu",
        "name": "Teknisk Ukeblad",
        "url": "https://www.tu.no/rss",
        "bydel": "Frogner",
        "weight": 0.4,
        "resolver": "text_match_bydel_fallback",
    },
    {
        "id": "kampanje",
        "name": "Kampanje",
        "url": "https://kampanje.com/rss",
        "bydel": "Gr\u00fcnerl\u00f8kka",
        "weight": 0.4,
        "resolver": "text_match_bydel_fallback",
    },
    {
        "id": "nho",
        "name": "NHO",
        "url": "https://www.nho.no/rss",
        "bydel": "Frogner",
        "weight": 0.4,
        "resolver": "text_match_bydel_fallback",
    },
    {
        "id": "uio",
        "name": "Universitetet i Oslo",
        "url": "https://www.uio.no/om/aktuelt/aktuelle-saker/?vrtx=feed",
        "bydel": "Nordre Aker",  # Blindern ligger her
        "weight": 0.6,
        "resolver": "fixed_bydel",
    },
    {
        "id": "dagsavisen",
        "name": "Dagsavisen",
        "url": "https://www.dagsavisen.no/rss",
        "bydel": "St. Hanshaugen",
        "weight": 0.5,
        "resolver": "text_match_bydel_fallback",
    },
]

HTML_SOURCES = [
    {
        "id": "kjelsaas",
        "name": "Kjels\u00e5s IL",
        "scraper": "kjelsaas",
        "bydel": "Nordre Aker",
        "urls": ["https://www.kjelsaas.no/"],
        "limit": 12,
        "weight": 0.5,
    },
    {
        # Meetup Oslo find-page \u2014 scraper __NEXT_DATA__ for inntil 15 events.
        # Categori-fast = 'arrangement'; bydel utledes fra venue-navn.
        "id": "meetup-oslo",
        "name": "Meetup Oslo",
        "scraper": "meetup-oslo",
        "bydel": "Frogner",
        "urls": ["https://www.meetup.com/find/?location=no--Oslo&source=EVENTS"],
        "limit": 15,
        "weight": 0.4,
    },
    {
        # Skiforbundet terminliste filtrert paa Oslo Skikrets. Henter
        # alpinrenn, langrenn, hopp etc i Oslo + omegn.
        "id": "skiforbundet-oslo",
        "name": "Skiforbundet (Oslo Skikrets)",
        "scraper": "skiforbundet-terminliste",
        "krets": "Oslo Skikrets",
        "bydel": "Vestre Aker",
        "urls": ["https://www.skiforbundet.no/terminliste/"],
        "limit": 30,
        "weight": 0.5,
    },
    {
        # Operaen i Bjorvika — opera + ballett + konserter.
        "id": "operaen",
        "name": "Operaen",
        "scraper": "operaen",
        "bydel": "Gamle Oslo",
        "urls": ["https://operaen.no/forestillinger/"],
        "limit": 12,
        "weight": 0.6,
    },
    {
        # Nationaltheatret — Stortingsgata 15, sentrum (St. Hanshaugen-naer).
        "id": "nationaltheatret",
        "name": "Nationaltheatret",
        "scraper": "nationaltheatret",
        "bydel": "St. Hanshaugen",
        "urls": ["https://www.nationaltheatret.no/forestillinger/"],
        "limit": 15,
        "weight": 0.6,
    },
    {
        "id": "iltry",
        "name": "IL Try",
        "scraper": "iltry",
        "bydel": "Vestre Aker",
        "urls": ["https://il-try.no/category/1"],
        "limit": 12,
        "weight": 0.5,
    },
    {
        "id": "kondis",
        "name": "Kondis.no",
        "scraper": "kondis",
        "urls": ["https://www.kondis.no/"],
        "limit": 20,
        "weight": 0.4,
    },
    {
        "id": "politi-oslo",
        "name": "Oslo politidistrikt",
        "scraper": "politi-oslo",
        "bydel": "Frogner",
        "urls": ["https://www.politiet.no/nyheter-og-presse/oslo"],
        "limit": 15,
        "weight": 0.6,
    },
    {
        "id": "ruter-avvik",
        "name": "Ruter avvik",
        "scraper": "ruter-sx",
        "bydel": "Frogner",
        "urls": ["https://api.entur.io/realtime/v1/rest/sx?datasetId=RUT&maxSize=100"],
        "limit": 25,
        "weight": 0.5,
    },
    {
        "id": "oslomet",
        "name": "OsloMet",
        "scraper": "oslomet",
        "bydel": "Nordre Aker",
        "urls": [
            "https://www.oslomet.no/forskning/forskningsnyheter",
        ],
        "limit": 12,
        "weight": 0.5,
    },
    {
        "id": "bi-business-review",
        "name": "BI Business Review",
        "scraper": "bi",
        "bydel": "Nordre Aker",
        "urls": [
            "https://www.bi.no/forskning/business-review/",
        ],
        "limit": 10,
        "weight": 0.4,
    },
    {
        "id": "deichman-aktuelt",
        "name": "Deichman",
        "scraper": "deichman",
        "bydel": "Gamle Oslo",
        "urls": [
            "https://www.deichman.no/aktuelt",
        ],
        "limit": 15,
        "weight": 0.5,
    },
    {
        "id": "vartoslo",
        "name": "Vårt Oslo",
        "scraper": "vartoslo",
        "urls": [
            "https://www.vartoslo.no/",
        ],
        "limit": 30,
        "weight": 0.6,
    },
    {
        "id": "bym-kunngjoringer",
        "name": "Bymiljøetaten kunngjøringer",
        "scraper": "bym-kunngjoringer",
        "bydel": "Frogner",
        "urls": ["https://www.oslo.kommune.no/etater-foretak-og-ombud/bymiljoetaten/kunngjoringer/"],
        "limit": 20,
        "weight": 0.5,
    },
    {
        "id": "skiforeningen",
        "name": "Skiforeningen",
        "scraper": "skiforeningen",
        "bydel": "Vestre Aker",
        "urls": ["https://www.skiforeningen.no/nyheter"],
        "limit": 20,
        "weight": 0.5,
    },
    {
        "id": "akersposten",
        "name": "Akersposten",
        "scraper": "akersposten",
        "bydel": "Vestre Aker",
        "urls": [
            "https://akersposten.no/",
            # /minakersposten har eget redaksjonelt utvalg som ofte ikke
            # vises pa forsiden — ekstra dekning av kultur- og leserstoff.
            "https://www.akersposten.no/minakersposten",
        ],
        "limit": 30,
        "weight": 0.6,
    },
]


def tag_includes_bydel(tags, bydel):
    needle = f"Bydel {bydel}".lower()
    return any(needle in (t or "").lower() for t in tags)


def resolve_oslo_kommune_tags(entry):
    tags = [t.get("term", "") for t in entry.get("tags", [])]
    for b in BYDELER:
        if tag_includes_bydel(tags, b):
            return b
    return None


def resolve_groruddalen(entry):
    haystack = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    for b in ("Alna", "Bjerke", "Grorud", "Stovner"):
        if b.lower() in haystack:
            return b
    return "Grorud"


def _match_word(needle: str, haystack: str) -> bool:
    """Enkel ord-grense-match uten regex: sjekk at tegnene rundt forekomsten
    ikke er bokstaver. Taaler aeaao i naboposisjon."""
    import re
    letters = r"[a-z\u00e6\u00f8\u00e5\u00fc]"
    pat = r"(?<!" + letters + r")" + re.escape(needle) + r"(?!" + letters + r")"
    return re.search(pat, haystack) is not None


def resolve_text_match_bydel(entry):
    """Match foerst paa bydel-navn, deretter paa stroek-tabell.

    Bruker ord-grense slik at "Bjerke" ikke matcher "Bjerkeli".
    """
    haystack = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    # 1) Eksakt bydel-navn (lengst foerst for aa unngaa prefix-match)
    order = sorted(BYDELER, key=lambda b: -len(b))
    for b in order:
        if _match_word(b.lower(), haystack):
            return b
    # 2) Stroek-tabell (lengst foerst)
    stroek_order = sorted(STROEK_TIL_BYDEL.keys(), key=lambda s: -len(s))
    for s in stroek_order:
        if _match_word(s, haystack):
            return STROEK_TIL_BYDEL[s]
    return None




def resolve_fixed_bydel(entry):
    """Dummy-resolver: faktisk bydel settes av fetcher fra kilden.

    Brukes naar en RSS-feed kun inneholder saker fra ett bestemt idrettslag
    eller omraade, saa alle saker tilordnes samme bydel direkte.
    """
    return None  # fetcher bruker source['bydel'] direkte


# Nasjonale kilder (vegvesen, politi, E24, TU, Kampanje, NHO) dekker hele
# landet. Vi filtrerer paa Oslo-relevans: bydel-/stroek-treff foerst, deretter
# stikkord som viser at saken handler om Oslo-omraadet.
_OSLO_KEYWORDS = [
    "oslo", "ring 1", "ring 2", "ring 3", "operatunnel", "svartdalstunnel",
    "ekebergtunnel", "festningstunnel", "tasen", "\u00e5sen", "carl berner",
    "majorstu", "grefsen", "storo", "br\u00f8bekk", "akershus", "stor-oslo",
    "e6 oslo", "e18 oslo",
    # Naering-relevante Oslo-stikkord
    "oslo b\u00f8rs", "osloborsen", "aker brygge", "tjuvholmen", "barcode",
    "bj\u00f8rvika", "sk\u00f8yen", "nydalen", "oslo kommune", "schibsted",
    "dnb", "storebrand", "gjensidige", "aker asa", "equinor", "telenor",
]


SKIP = "__SKIP__"


def resolve_text_match_bydel_fallback(entry):
    """Som text_match_bydel, men returnerer SKIP naar saken ikke virker
    Oslo-relevant i det hele tatt (slik at nasjonale RSS-feeds filtreres)."""
    b = resolve_text_match_bydel(entry)
    if b:
        return b
    haystack = (
        (entry.get("title") or "")
        + " "
        + (entry.get("summary") or "")
    ).lower()
    OSLO_KEYWORDS = (
        "oslo", "groruddalen", "holmenkollen", "tøyen", "toyen",
        "frogner", "ullern", "sentrum",
    )
    for kw in OSLO_KEYWORDS:
        if kw in haystack:
            return None
    return SKIP


RESOLVERS = {
    "oslo_kommune_tags": resolve_oslo_kommune_tags,
    "groruddalen": resolve_groruddalen,
    "text_match_bydel": resolve_text_match_bydel,
    "text_match_bydel_fallback": resolve_text_match_bydel_fallback,
    "fixed_bydel": resolve_fixed_bydel,
}
