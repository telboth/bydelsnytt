"""Regelbasert kategorisering av saker.

Modulen er bevisst enkel: ord-i-ordbok mot tittel + sammendrag. Den første
kategorien som får en match, vinner. Ved ingen match får saken "annet".
Liste-rekkefølgen er prioritetsrekkefølgen.
"""
from __future__ import annotations

import re
from typing import Iterable

# Tuple av (kategori, liste av ord/fraser). Rekkefølgen bestemmer prioritet.
# Ordene er case-insensitive hele-ord-matcher (inkludert enkle bøyinger).
RULES: list[tuple[str, list[str]]] = [
    ("politikk", [
        "bydelsutvalg", "bydelsreform", "byrådet", "byråd", "bystyre",
        "høring", "vedtak", "budsjett", "politisk møte", "utvalg",
        "komité", "valgkamp", "sak i komit", "kommunestyr",
    ]),
    ("skole", [
        "skole", "elev", "barnehage", "osloskolen", "sfo", "aks",
        "lærer", "rektor", "1. trinn", "10. trinn", "mellomtrinn",
        "ungdomsskole", "barneskole", "videregåend", "utdanning",
        "universitet", "uio", "høgskole", "studenter", "studium",
        "forsker", "forskning", "pensum", "fakultet", "phd",
    ]),
    ("idrett", [
        "idrettslag", "fotball", "håndball", "hockey", "allidrett",
        "kamp", "serie", "turnering", "cup", "klubb", "trening",
        "keeper", "turn", "ski ", "langrenn", "alpint", "obik",
        "bedriftsserie", "idrettsforening", "idrettsskole", "toppserien",
        " il ", " il.", "fk ", "turnforening",
    ]),
    ("trafikk", [
        "trafikk", "bymiljøetaten", "fartsgrense", "gate", "sykkelsti",
        "sykkelfelt", "kollektiv", "ruter", "bane", "bus ", "fartsdemping",
        "stengt", "omkjøring", "bro", "tunnel", "parkeringsavgift",
        "vegarbeid", "anleggsarbeid",
    ]),
    ("helse", [
        "helse", "sykehus", "lege", "fastlege", "hjemmetjeneste",
        "dagaktivitet", "seniorsenter", "eldreomsorg", "omsorg",
        "rehabiliter", "psykisk", "rus", "tannhelse", "vaksine",
    ]),
    ("kultur", [
        "museum", "kunst", "utstilling", "bibliotek", "deichman",
        "teater", "konsert", "kor", "kulturhus", "kulturdager",
        "leseløft", "litteratur", "kunstverk", "kunstner",
    ]),
    ("arrangement", [
        "festival", "marked", "arrangement", "fest", "åpen dag",
        "familiedag", "konferanse", "seminar", "åpen hage",
        "loppemarked", "gatelek", "dugnad", "åpning", "innvielse",
        "17. mai", "sankthans", "julemarked",
    ]),
    ("naering", [
        "restaurant", "bar", "kafé", "kafe", "butikk", "næring",
        "eiendomsmegler", "boligsalg", "boligmarked", "meglerhus",
        "bedrift", "gründer", "næringsliv", "arbeidsledighet",
        # Børs / finans
        "oslo børs", "børs", "aksje", "aksjer", "emisjon", "ipo",
        "notering", "utbytte", "kvartalsrapport", "kvartalsresultat",
        "årsregnskap", "omsetning", "driftsresultat", "fusjon",
        "oppkjøp", "konkurs", "gjeldsforhandling",
        # Startup / tech
        "startup", "scaleup", "venturefond", "investor",
        "vc-fond", "såkornfond", "innovasjon", "accelerator",
        "finansiering", "kapitalinnhenting",
        # Bransjer
        "netthandel", "varehandel", "reiseliv", "turisme",
        "hotell", "cruise", "fintech",
        "energibransje", "energiselskap", "oljeselskap", "fornybar",
        "eiendom", "eiendomsutvikler", "næringseiendom",
        # Jobb / ansettelser
        "nyansatt", "permittering", "oppsigelse", "lederstilling",
        "ny sjef", "ny direktør", "rekruttering",
        # Stor-Oslo selskaper
        "dnb", "storebrand", "gjensidige", "schibsted", "equinor",
        "telenor", "aker asa", "yara", "nordea", "orkla",
    ]),
    ("sikkerhet", [
        "brann", "politi", "politiet", "innbrudd", "tyveri",
        "pågripelse", "kriminalitet", "vold ", "overfall",
        "evakuer", "ulykke", "skadet", "omkom", "truet",
    ]),
]

# Noen "byclue"-ord som alltid gir en bestemt kategori uansett posisjon
STRONG_HINTS = {
    "markastue": "arrangement",
    "bymiljøetaten": "trafikk",
    "bydelsutvalget": "politikk",
    "oslo børs": "naering",
    "oslomet": "skole",
}


def _build_patterns():
    """Prekompiler regex per regel (kjører én gang på import)."""
    pats = []
    for cat, words in RULES:
        parts = [re.escape(w.strip()) for w in words if w.strip()]
        pattern = re.compile(r"\b(?:" + "|".join(parts) + r")", re.IGNORECASE)
        pats.append((cat, pattern))
    strong = {re.compile(r"\b" + re.escape(w), re.IGNORECASE): cat
              for w, cat in STRONG_HINTS.items()}
    return pats, strong


_PATTERNS, _STRONG = _build_patterns()


def classify_story(title: str, summary: str = "") -> str:
    """Returner beste kategori (fallback: 'annet')."""
    text = (title or "") + " " + (summary or "")
    # Strong hints first
    for pat, cat in _STRONG.items():
        if pat.search(text):
            return cat
    # Regular rules in priority order
    for cat, pat in _PATTERNS:
        if pat.search(text):
            return cat
    return "annet"


def classify_all(stories: Iterable[dict]) -> list[dict]:
    """Oppdaterer 'category' på hver sak (in-place hvis felt mangler/er default)."""
    out = []
    for s in stories:
        # Respekter eksisterende ikke-default kategori (menneskelig kuratert)
        if s.get("category") and s["category"] != "annet":
            out.append(s)
            continue
        s = dict(s)
        s["category"] = classify_story(s.get("title", ""), s.get("summary", ""))
        out.append(s)
    return out


if __name__ == "__main__":
    tests = [
        ("Bydelsutvalget vedtar nytt budsjett", ""),
        ("Ny kafé åpner på Grünerløkka", ""),
        ("Røa IL arrangerer vårcup på Voldsløkka", ""),
        ("Bymiljøetaten stenger Ullevålsveien i helgen", ""),
        ("Festival i Vigelandsparken i juni", ""),
        ("Gamlebyen skole med leseløft", ""),
        ("Politiet rykket ut til brann", ""),
        ("Oslo Børs åpner med oppgang", ""),
        ("DNB leverer rekordresultat", ""),
        ("Startup henter 50 millioner", ""),
        ("UiO åpner nytt forskningssenter", ""),
        ("OsloMet utvider tilbud", ""),
    ]
    for t, s in tests:
        print(f"  {classify_story(t, s):14s} <- {t}")
