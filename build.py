#!/usr/bin/env python3
"""Build Bydelsnytt Oslo HTML — two versions (artifact + publish).

Schema per story:
  title   : str
  source  : str
  date    : str   (display)
  date_iso: str | None  (YYYY-MM-DD, used for period-filter + is_fresh)
  category: str   (one of CATEGORIES)
  summary : str   (3-4 lines of prose)
  url     : str

Kategorier:
  politikk, skole, idrett, kultur, trafikk, helse, næring, sikkerhet, arrangement, annet
"""
from datetime import datetime, timezone, timedelta
import json, html, os, sys, pathlib, urllib.parse

# Make the pipeline package importable when build.py is run directly
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from pipeline import locations as _loc
    from pipeline import cache as _cache
    from pipeline import health as _health
except Exception as _e:  # pragma: no cover - pipeline is optional
    _loc = None
    _cache = None
    _health = None
    print(f"[build] pipeline ikke tilgjengelig: {_e}", file=sys.stderr)

OSLO_TZ = timezone(timedelta(hours=2))  # CEST, april
NOW = datetime.now(OSLO_TZ)
TODAY_ISO = NOW.date().isoformat()
YESTERDAY_ISO = (NOW.date() - timedelta(days=1)).isoformat()
TIMESTAMP_ISO = NOW.isoformat(timespec="seconds")

_MONTHS_NO = [
    "", "januar", "februar", "mars", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "desember",
]
DATE_NO = f"{NOW.day}. {_MONTHS_NO[NOW.month]} {NOW.year}"


def _check_stories_freshness(stories_path: pathlib.Path, max_age_hours: float = 20.0) -> None:
    """Advar hvis stories.json er eldre enn max_age_hours — tegn paa at
    daglig RSS-kjoering har feilet eller at vi bygger paa stale data."""
    try:
        data = json.loads(stories_path.read_text(encoding="utf-8"))
        updated = data.get("updatedAt")
        if not updated:
            print("[build] ADVARSEL: stories.json mangler updatedAt", file=sys.stderr)
            return
        t = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age_h = (datetime.now(t.tzinfo) - t).total_seconds() / 3600.0
        if age_h > max_age_hours:
            print(
                f"[build] ADVARSEL: stories.json er {age_h:.1f} timer gammel "
                f"(updatedAt={updated}). Daglig RSS-kjoering kan ha feilet.",
                file=sys.stderr,
            )
        else:
            print(f"[build] stories.json er {age_h:.1f} timer gammel — OK")
    except FileNotFoundError:
        print(f"[build] ADVARSEL: stories.json ikke funnet: {stories_path}", file=sys.stderr)
    except Exception as e:
        print(f"[build] kunne ikke sjekke freshness: {e}", file=sys.stderr)


_check_stories_freshness(pathlib.Path(__file__).resolve().parent / "stories.json")

CATEGORIES = [
    ("politikk", "Politikk"),
    ("skole", "Skole"),
    ("idrett", "Idrett"),
    ("kultur", "Kultur"),
    ("trafikk", "Trafikk"),
    ("helse", "Helse"),
    ("naering", "Næring"),
    ("sikkerhet", "Sikkerhet"),
    ("arrangement", "Arrangement"),
    ("annet", "Annet"),
]
CAT_LABEL = dict(CATEGORIES)

def is_fresh(story_or_date):
    """True hvis saken foerst ble sett i loepet av siste 24 timer.

    Tar enten en hel story-dict (foretrukket) eller en ren date_iso-string
    for bakoverkompatibilitet. Bruker first_seen_iso foerst — det er den
    mest paalitelige markoeren for "denne dukket akkurat opp hos oss", og
    er robust mot scrapere som re-stamper date_iso paa hver kjoering.
    Faller tilbake til date_iso hvis first_seen_iso mangler.
    """
    # Back-compat: rent string-argument behandles som date_iso
    if isinstance(story_or_date, str) or story_or_date is None:
        d = story_or_date or ""
        if not d:
            return False
        return YESTERDAY_ISO <= d <= TODAY_ISO

    story = story_or_date
    first_seen = (story.get("first_seen_iso") or "")[:10]
    if first_seen:
        return YESTERDAY_ISO <= first_seen <= TODAY_ISO
    d = story.get("date_iso") or ""
    if not d:
        return False
    return YESTERDAY_ISO <= d <= TODAY_ISO

# ---------------------------------------------------------------------------
# Innhold — 15 bydeler, kommunale kilder + aviser + skoler + idrettslag
# ---------------------------------------------------------------------------
BYDELER = [
    {
        "name": "Alna",
        "stories": [
            {
                "title": "13 millioner til viktige tiltak på Furuset",
                "source": "Oslo kommune – Aktuelt",
                "date": "April 2026",
                "date_iso": "2026-04-01",
                "category": "politikk",
                "summary": (
                    "Bydel Alna mottar 13 millioner kroner gjennom områdesatsingen i Oslo. "
                    "3 millioner går til boligmiljøprosjektet på Furuset, mens 10 millioner "
                    "er satt av til midlertidige tiltak på Granstomta. Beboere, foreninger "
                    "og borettslag inviteres i april til å gi innspill på videre utvikling. "
                    "Midlene skal bidra til mer liv og trygghet i nabolaget."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-alna-far-midler-til-viktige-tiltak-pa-furuset",
            },
            {
                "title": "Over 2 millioner til fritidsaktiviteter for barn og unge",
                "source": "Oslo kommune – Aktuelt",
                "date": "April 2026",
                "date_iso": "2026-04-01",
                "category": "annet",
                "summary": (
                    "Bydel Alna har fått nye midler i 2026 som skal gjøre det lettere for barn "
                    "og unge å delta i fritidsaktiviteter uavhengig av familiens økonomi. "
                    "Midlene dekker utstyr, kontingent og transport, og forvaltes sammen med "
                    "lokale lag og foreninger. Målet er at ingen barn i bydelen skal stå "
                    "utenfor fritidstilbudet av økonomiske grunner."
                ),
                "url": "https://aktuelt.oslo.kommune.no/over-2-millioner-til-fritidsaktiviteter-for-barn-og-unge-i-bydel-alna",
            },
            {
                "title": "Politiske møter i april 2026",
                "source": "Oslo kommune – Aktuelt",
                "date": "14. april 2026",
                "date_iso": "2026-04-14",
                "category": "politikk",
                "summary": (
                    "Andre møterunde av totalt seks holdes i bydelsutvalg, komiteer og råd "
                    "denne våren. Møtet 14. april kl. 17:00 på Nabolagshuset på Trosterud "
                    "åpner med halvtime for publikum fra 17:00 til 17:30. Bydelsutvalget "
                    "behandler blant annet saker om frivillighet, oppvekst og områdesatsing. "
                    "Hele programmet ligger på bydelens nettside."
                ),
                "url": "https://aktuelt.oslo.kommune.no/politiske-moter-i-april-2026-bydel-alna",
            },
            {
                "title": "Furuset IF: bred vårsesong for barn og ungdom",
                "source": "Furuset IF",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "idrett",
                "summary": (
                    "Furuset IF ruller ut et bredt vårprogram med fotball, ishockey og "
                    "allidrett for barn og ungdom i bydelen. Klubben melder om god rekruttering "
                    "til jenteklassene og utvider treningstidene på Gran kunstgress. "
                    "Nye spillere ønskes velkommen gjennom hele sesongen, og klubben har "
                    "kontingentstøtte for familier som trenger det."
                ),
                "url": "https://www.furusetif.no/",
            },
        ],
    },
    {
        "name": "Bjerke",
        "stories": [
            {
                "title": "Byrådet vil kutte antall bydeler fra 15 til 8",
                "source": "Nettavisen",
                "date": "Oktober 2025 – løpende",
                "date_iso": "2025-10-01",
                "category": "politikk",
                "summary": (
                    "Byrådet har landet på åtte nye bydeler i Oslo. Bystyret skal vedta ny "
                    "organisering våren 2026. Bjerke er blant bydelene som kan bli slått "
                    "sammen med naboer i Groruddalen. Lokale politikere frykter at lokaldemokratiet "
                    "svekkes når enhetene blir større, mens byrådet peker på gevinster i "
                    "administrasjon og tjenestekvalitet."
                ),
                "url": "https://www.nettavisen.no/nyheter/vil-kutte-antall-bydeler-i-oslo-blir-rasende/s/5-95-2675995",
            },
            {
                "title": "Frivillighetsmidler 2026 — hjelp til søknader",
                "source": "Frivillig i Bjerke",
                "date": "Januar–april 2026",
                "date_iso": "2026-01-15",
                "category": "annet",
                "summary": (
                    "Bydelen tilbyr hjelp til å fylle ut søknader om frivillighetsmidler for 2026. "
                    "Frivillighetssentralen har publisert veiledning, informasjonsmøter og "
                    "kontaktpunkter for lokale foreninger og ildsjeler. Flere borettslag, kor "
                    "og idrettslag har allerede fått støtte til mindre prosjekter. Søknadsfristen "
                    "er løpende inntil potten er tom."
                ),
                "url": "https://www.frivilligibjerke.no/post/trenger-du-hjelp-med-%C3%A5-fylle-ut-s%C3%B8knad-frivillighetsmidler-2026-bydel-bjerke",
            },
            {
                "title": "Bjerkealliansen utvider tilbudet for barn og unge",
                "source": "Bjerkealliansen",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "idrett",
                "summary": (
                    "Bjerkealliansen — samarbeidet mellom de lokale idrettslagene — utvider "
                    "fritidstilbudet til barn og unge på Årvoll, Linderud og Veitvet denne våren. "
                    "Alliansen tilbyr allidrett, håndball og fotball, med lavterskel-treninger "
                    "flere ganger i uken. Klubbene melder om særlig stor pågang til jenteklassene "
                    "og vurderer å sette opp ekstra partier."
                ),
                "url": "https://www.frivilligibjerke.no/",
            },
        ],
    },
    {
        "name": "Frogner",
        "stories": [
            {
                "title": "Park- og kunstkart er nå ferdig",
                "source": "Oslo kommune – Bydel Frogner",
                "date": "April 2026",
                "date_iso": "2026-04-10",
                "category": "kultur",
                "summary": (
                    "Bydelens park- og kunstkart er lansert og gjør det enkelt å utforske parker "
                    "og kunst i Frogner via nye digitale kart. Kartet viser alle offentlige "
                    "kunstverk, lekeplasser og grøntområder, og er tilgjengelig både på mobil "
                    "og desktop. Prosjektet er gjennomført i samarbeid med Kulturetaten og "
                    "lokale kunstnere."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-frogner/alle-nyheter/",
            },
            {
                "title": "Søker ny driver av Vestkanttorget lørdagsmarked",
                "source": "Oslo kommune – Aktuelt",
                "date": "Våren 2026",
                "date_iso": "2026-03-15",
                "category": "arrangement",
                "summary": (
                    "Bydel Frogner lyser ut driftskontrakt for lørdagsmarkedet på Vestkanttorget "
                    "for 2025 og 2026. Markedet er et populært samlingspunkt med lokale "
                    "produsenter, kunsthåndverk og mat hver lørdag gjennom sommerhalvåret. "
                    "Interesserte aktører kan sende inn søknad gjennom bydelens anskaffelsesportal. "
                    "Kontrakten har oppstart til våren."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-frogner-soker-ny-driver-av-lordagsmarkedet-pa-vestkanttorget",
            },
            {
                "title": "Boligsalget på Frogner går tregt",
                "source": "VG",
                "date": "April 2026",
                "date_iso": "2026-04-12",
                "category": "naering",
                "summary": (
                    "Eiendomsmeglere i Frogner melder om tregt marked denne våren, med lavere "
                    "omsetningstakt og lengre liggetid enn normalt. Renteoppgang og "
                    "usikkerhet i økonomien trekkes fram som hovedårsaker. Flere meglere "
                    "prøver å se lyst på situasjonen og peker på at dyre Frogner-leiligheter "
                    "historisk tåler kortvarige nedturer godt."
                ),
                "url": "https://www.vg.no/nyheter/i/K8rl84/boligsalget-paa-frogner-gaar-tregt-proever-aa-tenke-positivt",
            },
            {
                "title": "Monolitten IL: sterk start på fotballsesongen",
                "source": "Monolitten IL",
                "date": "April 2026",
                "date_iso": "2026-04-10",
                "category": "idrett",
                "summary": (
                    "Monolitten IL har startet vårsesongen med full kunstgress-aktivitet på "
                    "Frognerparken og Monolitt-banen. Både junior- og seniorlagene spiller "
                    "seriekamper i april, og klubben melder om rekordhøy påmelding til "
                    "fotballskolen i juni. Klubben samarbeider med lokale sponsorer om nytt "
                    "utstyr til jenteavdelingen."
                ),
                "url": "https://www.monolitten.no/",
            },
            {
                "title": "Njård melder om bred aktivitet på Frøen",
                "source": "Njård IL",
                "date": "Våren 2026",
                "date_iso": "2026-04-18",
                "category": "idrett",
                "summary": (
                    "Idrettslaget Njård har base på Frøen og rapporterer bred oppslutning om "
                    "både breddetilbud og satsingsgrupper denne våren. Klubben driver et av "
                    "byens største tilbud for barn i turn, håndball og friidrett, og tilbyr "
                    "allidrett og SFO-samarbeid med flere skoler i nærområdet. Klubben har "
                    "satt opp nye jenteparti i håndball for å møte etterspørselen."
                ),
                "url": "https://www.njard.no/",
            },
        ],
    },
    {
        "name": "Gamle Oslo",
        "stories": [
            {
                "title": "Grønland Gatelekfestival 25. april",
                "source": "Bydel Gamle Oslo",
                "date": "25. april 2026, kl 12–16",
                "date_iso": "2026-04-25",
                "category": "arrangement",
                "summary": (
                    "Interkulturelt Museum og lokale aktører arrangerer gatelekfestival på "
                    "Grønland lørdag 25. april kl. 12–16. Det blir klassiske gateleker, "
                    "musikk, matsalg og aktiviteter fra foreninger i nærmiljøet. Arrangementet "
                    "er gratis og åpent for hele familien. Gatelekfestivalen har vokst "
                    "betydelig de siste årene og er blitt en fast vårtradisjon."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-gamle-oslo/alle-nyheter/",
            },
            {
                "title": "Klar advarsel til bydelsreformen",
                "source": "Avisa Oslo",
                "date": "Våren 2026",
                "date_iso": "2026-03-20",
                "category": "politikk",
                "summary": (
                    "Grünerløkka, Gamle Oslo og Sagene uttrykker bekymring for byrådets "
                    "bydelsreform. Bydelslederne frykter at nærhet til innbyggerne svekkes "
                    "når bydelene slås sammen til større enheter. I en felles uttalelse "
                    "ber de byrådet om grundigere høring og bedre faglige utredninger før "
                    "bystyret tar endelig beslutning."
                ),
                "url": "https://www.ao.no/klar-advarsel-fra-gr-nerlokka-gamle-oslo-og-sagene-vi-er-bekymret/s/5-128-1234736",
            },
            {
                "title": "Gamlebyen skole med ny leseløft-satsing",
                "source": "Gamlebyen skole",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "skole",
                "summary": (
                    "Gamlebyen skole har i vår lansert et leseløft-prosjekt for 1.–4. trinn "
                    "med økt fokus på skjønnlitteratur og høytlesing. Prosjektet er et "
                    "samarbeid mellom skolen, Deichman Grønland og lokale forfattere. "
                    "Foreldre inviteres til lesegrupper på kveldstid, og skolen har satt "
                    "av ekstra tid i timeplanen til stillelesing for de yngste."
                ),
                "url": "https://gamlebyen.osloskolen.no/",
            },
            {
                "title": "Bymiljøetaten starter sommerarbeid langs Akerselva",
                "source": "Bymiljøetaten",
                "date": "April-mai 2026",
                "date_iso": "2026-04-18",
                "category": "trafikk",
                "summary": (
                    "Bymiljøetaten (BYM) starter vedlikeholdsarbeid langs Akerselva og i "
                    "Grønlandsparken denne våren. Nye benker, belysning og støttemurer settes "
                    "opp, og det blir midlertidige omlegginger for gående og syklende mellom "
                    "Kuba og Grønland. BYM oppfordrer beboere og næringsdrivende til å melde "
                    "inn skader og feil i gater og parker via byens meldeløsning."
                ),
                "url": "https://www.oslo.kommune.no/bymiljoetaten/",
            },
        ],
    },
    {
        "name": "Grorud",
        "stories": [
            {
                "title": "Fire ryddeaksjoner i Groruddalen 21. og 23. april",
                "source": "Groruddalen.no",
                "date": "21. og 23. april 2026",
                "date_iso": "2026-04-21",
                "category": "annet",
                "summary": (
                    "Bydel Grorud arrangerer fire ryddeaksjoner i Groruddalen denne uken — "
                    "tirsdag 21. og torsdag 23. april. Alle kan delta uansett alder, og "
                    "bydelen stiller med hansker, sekker og varme drikker på oppmøtestedene. "
                    "Etter aksjonene blir det pølsegrill og premietrekning for de som har "
                    "meldt seg på forhånd. Aksjonene er del av den årlige vårdugnaden."
                ),
                "url": "https://groruddalen.no/annonsorinnhold/informasjon-fra-bydel-grorud-april-2026/",
            },
            {
                "title": "Bydelsutvalgsmøte 29. april",
                "source": "Groruddalen.no",
                "date": "29. april 2026, kl 18:00",
                "date_iso": "2026-04-29",
                "category": "politikk",
                "summary": (
                    "Møte i Grorud bydelsutvalg holdes i Grorud bydelshus, Kakkelovnskroken 3, "
                    "kl. 18:00. Møtet sendes direkte på Bydel Groruds Facebook-side. "
                    "På sakskartet står blant annet budsjettoppfølging, områdesatsing "
                    "og høringsuttalelser om bydelsreformen. Publikum kan følge møtet "
                    "både fysisk og digitalt."
                ),
                "url": "https://groruddalen.no/annonsorinnhold/informasjon-fra-bydel-grorud-april-2026/",
            },
            {
                "title": "Gratis A2/B1 norskkurs starter 27. april",
                "source": "Groruddalen.no",
                "date": "Oppstart 27. april 2026",
                "date_iso": "2026-04-27",
                "category": "skole",
                "summary": (
                    "Integrering og Kompetanse Akademiet og Nettverkshuset tilbyr gratis "
                    "norskkurs på A2/B1-nivå for deg som vil videreutvikle språket med tanke "
                    "på jobb eller utdanning. Kurset går over flere uker med undervisning "
                    "to ganger i uken, og tar opp både skriftlig og muntlig norsk. Påmelding "
                    "skjer via Nettverkshuset."
                ),
                "url": "https://groruddalen.no/annonsorinnhold/informasjon-fra-bydel-grorud-april-2026/",
            },
            {
                "title": "Grorud IL arrangerer vårcup for aldersbestemte lag",
                "source": "Grorud IL",
                "date": "Mai 2026",
                "date_iso": "2026-04-15",
                "category": "idrett",
                "summary": (
                    "Grorud IL arrangerer tradisjonell vårcup på Grorud kunstgress i mai, "
                    "med påmelding åpen for lag fra 8 til 13 år. Cupen samler hundrevis av "
                    "barn fra hele Oslo Øst og er blitt et av klubbens viktigste arrangementer. "
                    "Klubben søker frivillige til kiosk, parkering og dommervirksomhet gjennom "
                    "helgen — alle bidrag mottas med takk."
                ),
                "url": "https://www.grorudil.no/",
            },
            {
                "title": "Lilloseter klar for vårsesong i Lillomarka",
                "source": "Lilloseter / Markastuer",
                "date": "April-mai 2026",
                "date_iso": "2026-04-19",
                "category": "arrangement",
                "summary": (
                    "Lilloseter i Lillomarka åpner vårsesongen med full servering i helgene "
                    "og utvidet tilbud i skoleferier. Markastuen er et populært utfartsmål for "
                    "turgåere, syklister og familier i Grorud og nabobydelene. Turlagene i "
                    "området arrangerer guidede vandringer fra Linderudkollen og Grorudparken "
                    "med innlagte stopp på stua."
                ),
                "url": "https://www.lilloseter.no/",
            },
        ],
    },
    {
        "name": "Grünerløkka",
        "stories": [
            {
                "title": "Flere trenger økonomisk bistand",
                "source": "Meravoslo.no",
                "date": "Våren 2026",
                "date_iso": "2026-04-05",
                "category": "helse",
                "summary": (
                    "Økt husleie og prisvekst gjør at stadig flere Grünerløkka-beboere oppsøker "
                    "bydelens sosialtjenester. Bydelen ser økt trykk også i 2026, særlig "
                    "blant enslige forsørgere og unge voksne. Sosialtjenesten melder om "
                    "ventetid på førstegangssamtale og oppfordrer innbyggere til å ta tidlig "
                    "kontakt dersom økonomien blir vanskelig."
                ),
                "url": "https://meravoslo.no/nyheter/tag/Grunerl%C3%B8kka",
            },
            {
                "title": "Storbyens Hjerte og Smerte 2026",
                "source": "Oslo kommune",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "arrangement",
                "summary": (
                    "Den nordiske storbykonferansen Storbyens Hjerte og Smerte kommer til "
                    "Oslo i 2026. Påmelding er åpnet, og flere bydeler deltar aktivt med "
                    "workshops og paneldebatter. Konferansen samler fagfolk, politikere og "
                    "ildsjeler fra hovedstedene i Skandinavia for å utveksle erfaringer om "
                    "byutvikling, sosialt arbeid og lokaldemokrati."
                ),
                "url": "https://meravoslo.no/nyheter/tag/Grunerl%C3%B8kka",
            },
            {
                "title": "Ny restaurant Rodeo på øvre Grünerløkka",
                "source": "Oslonytt",
                "date": "Mars/april 2026",
                "date_iso": "2026-04-02",
                "category": "naering",
                "summary": (
                    "Ny restaurant Rodeo har åpnet på øvre Grünerløkka med dumplings, gnocchi "
                    "og desserter. Over 120 restauranter er nå i drift i bydelen, og Grünerløkka "
                    "har festet grepet som Oslos tetteste matkvartal. Rodeo skal ha en uformell "
                    "profil med mindre retter til deling, og plan for kveldsåpen bar i helgene. "
                    "Omtalen fra Oslonytt er positiv."
                ),
                "url": "https://www.oslonytt.com/grunerlokka",
            },
            {
                "title": "Christiania Ballklubb: full fart i seriestart",
                "source": "Christiania Ballklubb",
                "date": "April 2026",
                "date_iso": "2026-04-18",
                "category": "idrett",
                "summary": (
                    "Christiania Ballklubb har kommet godt i gang med seriestart for både "
                    "senior- og juniorlagene. Klubben har økt medlemstallet med flere hundre "
                    "det siste året, og har nå aktivitet på Dælenenga, Jordal og Sofienberg "
                    "gjennom hele uken. Klubben jobber for bedre baner i bydelen og "
                    "samarbeider tett med Oslo Idrettskrets om kapasitet."
                ),
                "url": "https://www.christianiaballklubb.no/",
            },
        ],
    },
    {
        "name": "Nordre Aker",
        "stories": [
            {
                "title": "Byrådet foreslår sammenslåing med Sagene",
                "source": "Nordre Aker Budstikke",
                "date": "17. mars 2026",
                "date_iso": "2026-03-17",
                "category": "politikk",
                "summary": (
                    "Byrådet vil slå Nordre Aker sammen med Sagene som del av bydelsreformen. "
                    "Forslaget er på høring og vekker debatt blant lokalpolitikere. Flere "
                    "grupperinger i bydelsutvalget har varslet at de vil fraråde sammenslåingen, "
                    "mens byrådet peker på administrative gevinster. Høringsfrist er satt "
                    "til slutten av april."
                ),
                "url": "https://www.nab.no/dette-vil-byradet-skal-skje-med-nordre-aker/s/5-143-643289",
            },
            {
                "title": "Møter i politiske råd og utvalg i april",
                "source": "Oslo kommune – Aktuelt",
                "date": "April 2026",
                "date_iso": "2026-04-01",
                "category": "politikk",
                "summary": (
                    "Politiske møter i bydelen er åpne for publikum og starter med åpen "
                    "halvtime hvor alle kan stille spørsmål. Fullt møteprogram for bydelsutvalg, "
                    "komiteer og råd ligger på bydelens nettside. I april behandler utvalgene "
                    "blant annet budsjettoppfølging, helse- og oppvekstsaker og høringsuttalelse "
                    "om bydelsreformen."
                ),
                "url": "https://aktuelt.oslo.kommune.no/moter-i-politiske-rad-og-utvalg-i-bydel-nordre-aker-i-april",
            },
            {
                "title": "Nordre Aker Turnforening klar for stevne",
                "source": "Nordre Aker Turnforening",
                "date": "Mai 2026",
                "date_iso": "2026-04-12",
                "category": "idrett",
                "summary": (
                    "Nordre Aker Turnforening forbereder vårstevne i mai med deltakelse fra "
                    "barne- og ungdomsgrupper. Foreningen har utvidet tilbudet med nye "
                    "partier for foreldre-og-barn turn, og har fått god tilgang til Berg "
                    "flerbrukshall gjennom vinteren. Stevnet avsluttes med oppvisning og "
                    "kakeservering i hallen."
                ),
                "url": "https://www.nordreakerturn.no/",
            },
            {
                "title": "Kjelsås IL melder god vekst i barne- og ungdomsidretten",
                "source": "Kjelsås IL",
                "date": "Våren 2026",
                "date_iso": "2026-04-17",
                "category": "idrett",
                "summary": (
                    "Kjelsås IL rapporterer fortsatt god vekst i barne- og ungdomsidretten, "
                    "særlig innen fotball, håndball og ski. Klubben oppgraderer banefasilitetene "
                    "på Grefsen stadion og utvider treningstidene for jenter og ungdom. "
                    "Sportslig har Kjelsås etablert seg i øvre del av 1. divisjon i fotball, "
                    "og klubben samarbeider med lokale skoler om allidrett."
                ),
                "url": "https://www.kjelsaas.no/",
            },
            {
                "title": "Lyn ruller ut bred vårsesong på Kringsjå",
                "source": "FK Lyn / Lyn 1896",
                "date": "Våren 2026",
                "date_iso": "2026-04-16",
                "category": "idrett",
                "summary": (
                    "FK Lyn melder om fulle treningstider på Kringsjå Idrettspark denne våren, "
                    "med rekordpåmelding til aldersbestemte klasser både på gutte- og jentesiden. "
                    "Klubben satser videre på spillerutvikling og samarbeid med lokale skoler, "
                    "og jobber parallelt med å rehabilitere fasilitetene på Ullevaal. "
                    "A-laget åpner sesongen med tydelig opprykksambisjon."
                ),
                "url": "https://www.fklyn.no/",
            },
            {
                "title": "Ullevålseter klar for turister på ski og sykkel",
                "source": "Skiforeningen / Markastuer",
                "date": "April-mai 2026",
                "date_iso": "2026-04-20",
                "category": "arrangement",
                "summary": (
                    "Ullevålseter i Nordmarka er blant de mest besøkte markastuene og er åpen "
                    "for servering hele våren. Turgåere, syklister og skiløpere kan ta seg fram "
                    "via populære løyper fra Sognsvann, Kikut og Skjennungen. Stuen forbereder "
                    "sommersesong med utvidet kafedrift og samarbeider med Skiforeningen om "
                    "merking av sommerløyper."
                ),
                "url": "https://www.ullevalseter.no/",
            },
        ],
    },
    {
        "name": "Nordstrand",
        "stories": [
            {
                "title": "Holmlia + Nordstrand? Byrådets reformforslag",
                "source": "Nordstrands Blad",
                "date": "Våren 2026",
                "date_iso": "2026-03-20",
                "category": "politikk",
                "summary": (
                    "Byrådet foreslår å slå sammen Nordstrand med deler av Søndre Nordstrand "
                    "(Holmlia-området). Lokalpolitikere er delt i synet på forslaget — noen "
                    "mener det styrker tjenestetilbudet, andre advarer mot at det lokale "
                    "engasjementet vannes ut. Nordstrands Blad har dekket debatten tett, og "
                    "bydelsutvalget skal behandle høringsuttalelsen i april."
                ),
                "url": "https://www.noblad.no/holmlia-nordstrand-sant-dette-foreslar-byradet/s/5-56-1029829",
            },
            {
                "title": "Innbyggerdialog under Nordstrandsdagene",
                "source": "Oslo kommune – Aktuelt",
                "date": "Vår 2026",
                "date_iso": "2026-04-05",
                "category": "arrangement",
                "summary": (
                    "Bydelen arrangerer åpne innbyggerdialoger under Nordstrandsdagene for "
                    "å diskutere prioriteringer og tjenestetilbud. Bydelsdirektør, politikere "
                    "og fagfolk stiller til samtale, og innspillene blir fulgt opp i "
                    "senere politiske behandlinger. Dialogene er en fast tradisjon som "
                    "supplerer de formelle høringene."
                ),
                "url": "https://aktuelt.oslo.kommune.no/innbyggerdialog-under-nordstrandsdagene",
            },
            {
                "title": "Nordstrand IF styrker håndballsatsingen",
                "source": "Nordstrand IF",
                "date": "April 2026",
                "date_iso": "2026-04-10",
                "category": "idrett",
                "summary": (
                    "Nordstrand IF styrker håndballsatsingen med nye trenere og utvidede "
                    "treningstider på Niels Henrik Abels hall. Klubben er blant de største "
                    "breddeklubbene i Oslo på håndball, med lag i alle aldersklasser fra "
                    "6-åringer og oppover. Vårsesongen avsluttes med klubbcup og "
                    "sesongavslutning i juni."
                ),
                "url": "https://www.nordstrandif.no/",
            },
        ],
    },
    {
        "name": "Sagene",
        "stories": [
            {
                "title": "Skjult hagekafé Raade's åpner for sesongen",
                "source": "Meravoslo.no",
                "date": "April 2026",
                "date_iso": "2026-04-15",
                "category": "kultur",
                "summary": (
                    "I en sidegate på Sagene finner du hagekafeen Raade's, som åpner hagen "
                    "hver søndag og serverer hjemmelagede sveler. Stedet har blitt et lokalt "
                    "samlingspunkt for naboer som vil ha kaffe og sosialt samvær uten å "
                    "reise til sentrum. Omtalt i april av Meravoslo, som trekker fram den "
                    "avslappede atmosfæren og den enkle menyen."
                ),
                "url": "https://meravoslo.no/nyheter/tag/sagene",
            },
            {
                "title": "Advarsel om bydelsreformen",
                "source": "Avisa Oslo",
                "date": "Våren 2026",
                "date_iso": "2026-03-20",
                "category": "politikk",
                "summary": (
                    "Sammen med Grünerløkka og Gamle Oslo har Sagene signalisert bekymring "
                    "for byrådets forslag om færre og større bydeler. Bydelslederne peker "
                    "på svekket nærhet til innbyggerne som hovedbekymring, og ber byrådet "
                    "om lengre høring og bedre utredninger. Bystyret skal behandle reformen "
                    "senere i vår."
                ),
                "url": "https://www.ao.no/klar-advarsel-fra-gr-nerlokka-gamle-oslo-og-sagene-vi-er-bekymret/s/5-128-1234736",
            },
            {
                "title": "Sagene IF: fotballskole og åpen torsdagstrening",
                "source": "Sagene IF",
                "date": "Våren 2026",
                "date_iso": "2026-04-10",
                "category": "idrett",
                "summary": (
                    "Sagene IF arrangerer fotballskole i juni og holder åpen torsdagstrening "
                    "på Voldsløkka gjennom hele våren. Klubben er en av Oslos eldste og "
                    "tilbyr fotball, bandy, friidrett og boksing fra seks års alder. "
                    "Påmelding til fotballskolen er åpnet, og det er kontingentstøtte "
                    "tilgjengelig gjennom bydelen for familier som trenger det."
                ),
                "url": "https://www.sageneif.com/",
            },
            {
                "title": "OBIK åpner bedriftsserien på Voldsløkka",
                "source": "OBIK — Oslo Bedriftsidrett",
                "date": "Vår 2026",
                "date_iso": "2026-04-17",
                "category": "idrett",
                "summary": (
                    "Oslo Bedriftsidrettskrets (OBIK) sparker i gang bedriftsserien i fotball "
                    "og volleyball med flere kamper i uka på Voldsløkka, Bislett og Ekeberg. "
                    "Serien samler hundrevis av lag fra bedrifter og offentlige etater, og "
                    "bidrar til mye aktivitet på de åpne banene. Påmelding er fortsatt mulig i "
                    "flere grener, og OBIK opplever økt pågang fra mindre arbeidsplasser."
                ),
                "url": "https://www.obik.no/",
            },
        ],
    },
    {
        "name": "St. Hanshaugen",
        "stories": [
            {
                "title": "Storbyens Hjerte og Smerte-konferansen til Oslo",
                "source": "Oslo kommune",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "arrangement",
                "summary": (
                    "Oslo er vert for den nordiske storbykonferansen i 2026. Påmelding er "
                    "åpnet, og bydelen forventer oppmøte fra fagmiljøer over hele Norden. "
                    "Konferansen setter søkelys på sosialt arbeid, folkehelse og byutvikling "
                    "i de nordiske hovedstedene. Flere lokale aktører i St. Hanshaugen "
                    "bidrar med workshops."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-st-hanshaugen/",
            },
            {
                "title": "St. Hanshaugen Fotball starter nybegynnerkurs",
                "source": "St. Hanshaugen Fotball",
                "date": "April 2026",
                "date_iso": "2026-04-14",
                "category": "idrett",
                "summary": (
                    "St. Hanshaugen Fotball starter nybegynnerkurs for barn som aldri har "
                    "spilt fotball før. Kurset går over seks uker i april og mai, med "
                    "treninger på Ila kunstgress. Klubben satser på lavterskel-tilbud og "
                    "har egne trenere som følger opp kursdeltakerne. Fra høsten kan "
                    "deltakerne gå rett videre inn i ordinære lag."
                ),
                "url": "https://www.sthanshaugenfotball.no/",
            },
            {
                "title": "Bydelsutvalget behandler trafikksaker",
                "source": "Oslo kommune – Bydel St. Hanshaugen",
                "date": "April 2026",
                "date_iso": "2026-04-15",
                "category": "trafikk",
                "summary": (
                    "Bydelsutvalget i St. Hanshaugen behandler flere trafikksaker i april, "
                    "blant annet forslag om fartsdemping i Ullevålsveien og trafikksikkerhet "
                    "ved skolene. Forslagene er del av bydelens trafikksikkerhetsplan, og "
                    "innspill fra innbyggerne ble samlet inn i mars. Sakene ventes å gå "
                    "videre til Bymiljøetaten."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-st-hanshaugen/",
            },
        ],
    },
    {
        "name": "Stovner",
        "stories": [
            {
                "title": "Innspillsrunde: navn på nye bydeler",
                "source": "Groruddalen.no",
                "date": "Frist 24. april 2026",
                "date_iso": "2026-04-24",
                "category": "politikk",
                "summary": (
                    "Byrådet inviterer innbyggerne til å foreslå navn på de nye, sammenslåtte "
                    "bydelene. Stovner-beboere oppfordres til å bidra med forslag som fanger "
                    "lokal identitet og historie. Alle innsendte forslag vurderes av en "
                    "navnekomité før byrådet gir sin innstilling til bystyret. "
                    "Forslagene leveres via kommunens nettskjema."
                ),
                "url": "https://groruddalen.no/annonsorinnhold/informasjon-fra-bydel-stovner-mars-april-2026/",
            },
            {
                "title": "Norges første multikulturelle seniorsenter",
                "source": "Utrop",
                "date": "2026",
                "date_iso": "2026-03-15",
                "category": "helse",
                "summary": (
                    "Nettverk for Multikulturelt Sosialt Arbeid driver et nytt seniorsentertilbud "
                    "på Stovner Senter, med samvær, kurs og middag mandager og fredager. "
                    "Senteret er det første i sitt slag i Norge og henvender seg særlig "
                    "til eldre med minoritetsbakgrunn. Initiativet får støtte fra bydelen "
                    "og frivillige organisasjoner."
                ),
                "url": "https://www.utrop.no/nyheter/nytt/376672/",
            },
            {
                "title": "Leilighetsbrann slukket i Stovner",
                "source": "Aftenposten",
                "date": "20. april 2026",
                "date_iso": "2026-04-20",
                "category": "sikkerhet",
                "summary": (
                    "Politiet og brannvesenet rykket ut til leilighetsbrann øst i Oslo "
                    "søndag kveld. Brannen er slukket; ingen alvorlig skadet. Årsaken er "
                    "foreløpig ukjent, og politiet gjør tekniske undersøkelser i leiligheten. "
                    "Naboer ble evakuert en kort periode, men kunne vende tilbake til "
                    "boligene sine samme kveld."
                ),
                "url": "https://www.aftenposten.no/oslo/i/OkgvPA/brann-i-leilighet-i-oslo-er-slukket",
            },
            {
                "title": "Stovner flerbrukshall: nye tilbud til ungdom",
                "source": "Stovner flerbrukshall",
                "date": "Våren 2026",
                "date_iso": "2026-04-05",
                "category": "idrett",
                "summary": (
                    "Stovner flerbrukshall har utvidet åpningstidene for ungdom i helgene "
                    "og setter opp flere fritidsaktiviteter utenom ordinær trening. "
                    "Basketball, volleyball og innefotball går på rotasjon, og det er "
                    "gratis inngang for ungdom mellom 13 og 18 år. Bydelen melder om "
                    "god oppslutning og vurderer å utvide tilbudet til flere kvelder."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-stovner/",
            },
        ],
    },
    {
        "name": "Søndre Nordstrand",
        "stories": [
            {
                "title": "Vant Klarspråksprisen 2026",
                "source": "Oslo kommune – Aktuelt",
                "date": "April 2026",
                "date_iso": "2026-04-10",
                "category": "annet",
                "summary": (
                    "Bydel Søndre Nordstrand har vunnet Klarspråksprisen 2026 for sitt arbeid "
                    "med tydelig kommunikasjon. Prisen er en anerkjennelse av flere års "
                    "innsats gjennom Oslo sør-satsingen, og juryen trekker særlig fram "
                    "bydelens brev og søknadsskjema på flere språk. Bydelsadministrasjonen "
                    "har bygget opp egne klarspråk-verksteder internt."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-sondre-nordstand-vant-klarspraksprisen-2026",
            },
            {
                "title": "Bydelen foreslås splittet i reformen",
                "source": "Oslo kommune",
                "date": "Våren 2026",
                "date_iso": "2026-03-25",
                "category": "politikk",
                "summary": (
                    "Byrådet foreslår å splitte opp Bydel Søndre Nordstrand og fordele områdene "
                    "mellom Nordstrand og Østensjø. Innspillsfrist for navn er 24. april. "
                    "Forslaget er kontroversielt lokalt — mange peker på at bydelen har "
                    "en egen identitet som vil forsvinne. Bydelsutvalget avgir høringsuttalelse "
                    "før bystyrebehandlingen."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-sondre-nordstand-vant-klarspraksprisen-2026",
            },
            {
                "title": "Deltar i forskningsprosjektet SAFE@HOME",
                "source": "Oslo kommune – Aktuelt",
                "date": "2026",
                "date_iso": "2026-03-01",
                "category": "helse",
                "summary": (
                    "Bydelen deltar i forskningsprosjektet SAFE@HOME, som ser på trygghet "
                    "og mestring i eget hjem for eldre. Prosjektet skal utvikle verktøy "
                    "som gjør det enklere å bo hjemme lenger, og Søndre Nordstrand er valgt "
                    "som pilotbydel på grunn av sammensatt befolkning og bredt tjenestetilbud. "
                    "Resultater forventes publisert i 2027."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-sondre-nordstrand-deltar-i-forskningsprosjektet-safe-home",
            },
            {
                "title": "Holmlia SK: breddeidrett i vekst",
                "source": "Holmlia SK",
                "date": "Våren 2026",
                "date_iso": "2026-04-12",
                "category": "idrett",
                "summary": (
                    "Holmlia SK opplever solid vekst på breddeidrett denne våren, med flere "
                    "nye medlemmer i både fotball og håndball. Klubben har bygget ut "
                    "treningstider på Holmlia kunstgress og samarbeider med lokale skoler "
                    "om tilbud etter skoletid. Holmlia SK får støtte fra Oslo sør-satsingen "
                    "og har kontingentstøtte for familier som trenger det."
                ),
                "url": "https://www.holmliask.no/",
            },
        ],
    },
    {
        "name": "Ullern",
        "stories": [
            {
                "title": "Oslo vert for Storbyens Hjerte og Smerte 2026",
                "source": "Oslo kommune",
                "date": "Våren 2026",
                "date_iso": "2026-04-01",
                "category": "arrangement",
                "summary": (
                    "Ullern er blant bydelene som deltar i den nordiske storbykonferansen "
                    "Storbyens Hjerte og Smerte, som arrangeres i Oslo i 2026. Bydelen "
                    "stiller med eget innspill om eldreomsorg og boligpolitikk. Konferansen "
                    "samler fagfolk fra hele Norden og er en arena for erfaringsutveksling "
                    "mellom storbyene."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-ullern/",
            },
            {
                "title": "OBOS Miniligaen hos Ullern for 6–9-åringer",
                "source": "Ullern IF",
                "date": "Våren 2026",
                "date_iso": "2026-04-15",
                "category": "idrett",
                "summary": (
                    "Ullern IF arrangerer OBOS Miniligaen for 6–9-åringer med lavterskel-fotball "
                    "gjennom våren. Serien legges opp uten tabeller og med vekt på mestring "
                    "og spilleglede. Kampene spilles på Ullernbanen og i nærliggende klubber, "
                    "og alle barn får spille mye uansett ferdighetsnivå. Klubben melder "
                    "om rekordstort antall påmeldte lag."
                ),
                "url": "https://www.ullernif.no/",
            },
            {
                "title": "Ullern skole inviterer til vårkonsert",
                "source": "Ullern skole",
                "date": "Mai 2026",
                "date_iso": "2026-04-10",
                "category": "skole",
                "summary": (
                    "Ullern skole inviterer til vårkonsert i mai med elever fra både musikk- "
                    "og dramalinjen. Konserten er åpen for alle, og inntekter fra kaffesalg "
                    "går til skolens elevråd. Elevene har jobbet med et bredt program som "
                    "strekker seg fra klassisk til moderne pop, og musikklærerne melder om "
                    "høyt nivå i år."
                ),
                "url": "https://ullern.vgs.no/",
            },
        ],
    },
    {
        "name": "Vestre Aker",
        "stories": [
            {
                "title": "Bydelsutvalget møtes i april-mai",
                "source": "Oslo kommune – Aktuelt",
                "date": "April-mai 2026",
                "date_iso": "2026-04-15",
                "category": "politikk",
                "summary": (
                    "Bydelsutvalget møtes på Sørkedalen skole. Alle møter er åpne for publikum "
                    "og starter med åpen halvtime hvor innbyggere kan stille spørsmål. "
                    "På sakskartet står blant annet budsjettoppfølging, trafikksikkerhet "
                    "og høringsuttalelse om bydelsreformen. Hele møteprogrammet med "
                    "innkallinger og protokoller ligger på bydelens nettside."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-vestre-aker-politiske-motedatoer-i-april-mai",
            },
            {
                "title": "Budsjettforslag 2026 og økonomiplan 2026–2029",
                "source": "Oslo kommune – Aktuelt",
                "date": "Vår 2026",
                "date_iso": "2026-04-05",
                "category": "politikk",
                "summary": (
                    "Bydelsdirektørens forslag til budsjett for 2026 og økonomiplan 2026–2029 "
                    "er lagt fram til politisk behandling. Forslaget prioriterer oppvekst, "
                    "helse og eldre, og peker på stramme økonomiske rammer i årene som kommer. "
                    "Det legges opp til mindre kutt i administrasjon for å skjerme tjenester "
                    "til innbyggerne. Endelig budsjett vedtas av bydelsutvalget."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-vestre-aker-bydelsdirektorens-forslag-til-budsjett-2026-og-okonomiplan-2026-2029",
            },
            {
                "title": "Etterlyser trafikksikkerhetsinnspill",
                "source": "Oslo kommune – Aktuelt",
                "date": "Vår 2026",
                "date_iso": "2026-04-10",
                "category": "trafikk",
                "summary": (
                    "Bydelen ber innbyggere om innspill til trafikksikkerhetstiltak for 2026 — "
                    "uoversiktlige kryss, høy fart, manglende gangfelt og lignende. "
                    "Alle innspill kan sendes via bydelens nettskjema, og blir vurdert av "
                    "trafikkfaglig rådgiver før de oversendes Bymiljøetaten. Mange tiltak "
                    "rundt skoler og fritidsanlegg prioriteres særskilt."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-vestre-aker-forslag-til-trafikksikkerhetstiltak-for-2026",
            },
            {
                "title": "Vestre Aker Skiklub avslutter vintersesongen",
                "source": "Vestre Aker Skiklub",
                "date": "April 2026",
                "date_iso": "2026-04-15",
                "category": "idrett",
                "summary": (
                    "Vestre Aker Skiklub markerer slutten på en sterk vintersesong med "
                    "sesongavslutning og klubbfest for alle aldersgrupper. Klubben har hatt "
                    "stor oppslutning både på langrenn og alpint i Holmenkollmarka og "
                    "Tryvann. Flere unge løpere har tatt seg fram i kretsmesterskapene, og "
                    "klubben går nå over i barmarkstrening gjennom sommeren."
                ),
                "url": "https://vestreakerskiklub.no/",
            },
            {
                "title": "Heming IL: stor vårsesong for barn og ungdom",
                "source": "Heming IL",
                "date": "Våren 2026",
                "date_iso": "2026-04-18",
                "category": "idrett",
                "summary": (
                    "Heming IL på Slemdal melder om rekordpåmelding til vårens fotball- og "
                    "tennisgrupper, og rapporterer også gode tall for nye rekrutter i alpint og "
                    "langrenn. Klubben har utvidet allidrettstilbudet for de minste på Gressbanen, "
                    "og samarbeider med skolene i nærområdet om skolefotball og idrettsskole. "
                    "Nye utøvere tas fortsatt inn i flere grener."
                ),
                "url": "https://www.heming.no/",
            },
            {
                "title": "Røa IL markerer 100 år og breddesatsing",
                "source": "Røa IL",
                "date": "2026",
                "date_iso": "2026-04-15",
                "category": "idrett",
                "summary": (
                    "Røa IL markerer 100-årsjubileum i 2026 og har lagt opp til et bredt program "
                    "med jubileumskamper, klubbhelg og åpen dag på Røabanen. Damefotballen "
                    "fortsetter sin satsing i Toppserien, samtidig som klubben prioriterer "
                    "breddetilbudet for barn og unge. Klubben har kontingentstøtteordning og "
                    "utstyrsbank for familier som trenger det."
                ),
                "url": "https://www.roail.no/",
            },
            {
                "title": "Skiforeningen åpner for sommerbruk i Holmenkollen",
                "source": "Skiforeningen",
                "date": "Mai-juni 2026",
                "date_iso": "2026-04-20",
                "category": "arrangement",
                "summary": (
                    "Skiforeningen legger om driften fra vinter- til sommersesong i Holmenkollen "
                    "og Nordmarka. Skimuseet holder åpent hele våren, og foreningen starter opp "
                    "turgrupper, barmarkstrening og guidede historiske vandringer fra Frognerseteren. "
                    "Nytt av året er et utvidet tilbud om lavterskel familieturer med kart og "
                    "kompass-opplæring i marka."
                ),
                "url": "https://www.skiforeningen.no/",
            },
            {
                "title": "Kobberhaughytta klar for vårsesong i Nordmarka",
                "source": "DNT Oslo og Omegn / Markastuer",
                "date": "April 2026",
                "date_iso": "2026-04-19",
                "category": "arrangement",
                "summary": (
                    "Kobberhaughytta i Nordmarka er åpen for servering og overnatting gjennom "
                    "hele vårsesongen. Markastuen har økt kapasiteten etter ombygging og melder "
                    "om stor pågang av turgåere i helgene. Flere tur-løyper fra Frognerseteren, "
                    "Skjennungen og Løvlia er tilgjengelige både for gående og syklende, og "
                    "lokale turlag arrangerer familieturer med innlagte stopp på hytta."
                ),
                "url": "https://www.dntoslo.no/hytter/kobberhaughytta/",
            },
            {
                "title": "Try IL utvider breddetilbudet på Oppsal/Skullerud",
                "source": "Try IL",
                "date": "Våren 2026",
                "date_iso": "2026-04-17",
                "category": "idrett",
                "summary": (
                    "Try IL utvider tilbudet på Skullerud denne våren med nye parti i allidrett, "
                    "fotball og turn for barn og ungdom. Klubben melder om stor pågang til "
                    "jenteidrett og samarbeider med lokale skoler om fritidstilbud for mellomtrinnet. "
                    "Try har også utvidet tilbudet om rimelig leie av klubbhuset til "
                    "barnebursdager og nabolagsarrangementer."
                ),
                "url": "https://www.tryil.no/",
            },
        ],
    },
    {
        "name": "Østensjø",
        "stories": [
            {
                "title": "Bøler dagaktivitet flytter 27. april",
                "source": "Oslo kommune – Aktuelt",
                "date": "27. april 2026",
                "date_iso": "2026-04-27",
                "category": "helse",
                "summary": (
                    "Bøler dagaktivitet åpner i nye lokaler i Gamle Enebakkvei 48, "
                    "samlokalisert med Skullerud dagaktivitet. Flytting skjer 27. april. "
                    "De nye lokalene gir bedre plass til gruppeaktiviteter, kjøkken og "
                    "personalet kan samarbeide tettere. Brukere og pårørende har fått "
                    "egen orientering om overgangen."
                ),
                "url": "https://aktuelt.oslo.kommune.no/nytt-dagaktivitetstilbud-i-ostensjo-bydel",
            },
            {
                "title": "Bydelsutvalgsmøte 27. april",
                "source": "Oslo kommune",
                "date": "27. april 2026",
                "date_iso": "2026-04-27",
                "category": "politikk",
                "summary": (
                    "Politikerne tildeler frivillighetsmidler og behandler forslag om "
                    "endringer ved fritidsklubbene og Lille Langerud barnehage. På sakskartet "
                    "står også budsjettoppfølging og høringsuttalelse om bydelsreformen. "
                    "Møtet er åpent for publikum med åpen halvtime i starten. "
                    "Protokollen publiseres på bydelens nettside uken etter."
                ),
                "url": "https://www.oslo.kommune.no/bydeler/bydel-ostensjo/alle-nyheter/",
            },
            {
                "title": "Bydelsreformen: Østensjø blir del av større bydel sør",
                "source": "Oslo kommune – Aktuelt",
                "date": "Våren 2026",
                "date_iso": "2026-03-25",
                "category": "politikk",
                "summary": (
                    "Etter høring vil byrådet ha 8 bydeler, og Oslo sør får to store bydeler. "
                    "Østensjø er en del av dette kartet. Navneforslag-frist er 24. april. "
                    "Bydelsadministrasjonen har spilt inn en rekke forslag til byrådet om "
                    "hvordan tjenester bør organiseres for å opprettholde nærhet til "
                    "innbyggerne i den nye, større bydelen."
                ),
                "url": "https://aktuelt.oslo.kommune.no/bydel-ostensjo-bydelsadministrasjonens-innspill-til-bydelsreformen",
            },
            {
                "title": "Østensjø skole med miljøprosjekt våren 2026",
                "source": "Østensjø skole",
                "date": "Våren 2026",
                "date_iso": "2026-04-08",
                "category": "skole",
                "summary": (
                    "Østensjø skole kjører miljøprosjekt denne våren med fokus på Østensjøvannet "
                    "og det lokale fuglelivet. Elevene på mellomtrinnet samarbeider med "
                    "Østensjøvannets Venner om feltstudier og opprydding langs vannet. "
                    "Prosjektet avsluttes med en utstilling på skolen i juni, og deler av "
                    "arbeidet inngår i elevenes naturfagsvurdering."
                ),
                "url": "https://ostensjo.osloskolen.no/",
            },
            {
                "title": "Rustad IL: god rekruttering til fotball og ski",
                "source": "Rustad IL",
                "date": "Våren 2026",
                "date_iso": "2026-04-16",
                "category": "idrett",
                "summary": (
                    "Rustad IL på Bøler melder om god rekruttering til både fotball- og "
                    "skigruppen denne sesongen. Klubben har bygget ut kunstgresset og starter "
                    "vårsesong med ekstra treningsøkter for de aldersbestemte klassene. "
                    "Skigruppen arrangerer barmarkstrening gjennom våren, og klubben inviterer "
                    "også til familiedag på Rustadsaga til sommeren."
                ),
                "url": "https://www.rustadil.no/",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Integrer stories.json (fra pipeline/run.py) — legger til auto-hentede saker
# ---------------------------------------------------------------------------
def _ingest_cache(bydeler_list):
    """Merge RSS-saker fra stories.json inn i bydel-listen.

    * Saker med eksisterende url blir ikke duplikert (hardkodet sak vinner).
    * Nye saker legges bak de hardkodete i respektive bydel.
    """
    if _cache is None:
        return bydeler_list
    try:
        cached = _cache.load().get("stories", [])
    except Exception as e:
        print(f"[build] kunne ikke lese stories.json: {e}", file=sys.stderr)
        return bydeler_list
    if not cached:
        return bydeler_list

    by_name = {b["name"]: b for b in bydeler_list}
    # Known URLs per bydel for idempotency
    known = {
        b["name"]: {s.get("url", "").rstrip("/") for s in b["stories"]}
        for b in bydeler_list
    }

    for s in cached:
        if s.get("hidden"):
            continue  # kryss-kilde-dublett, representert av primary-saken
        bydel = s.get("bydel")
        if not bydel or bydel not in by_name:
            continue
        url_key = (s.get("url") or "").rstrip("/")
        if url_key in known[bydel]:
            continue
        # Map cache-struktur til build-skjema
        display_date = s.get("date_iso", "")[:10] or ""
        story = {
            "title": s.get("title", ""),
            "source": s.get("source", ""),
            "source_id": s.get("source_id", ""),
            "date": display_date,
            "date_iso": s.get("date_iso"),
            "category": s.get("category", "annet"),
            "summary": s.get("summary", ""),
            "url": s.get("url", ""),
            "first_seen_iso": s.get("first_seen_iso"),
            "extra_sources": s.get("extra_sources") or [],
            "image_url": s.get("image_url") or "",
            "event_date": s.get("event_date") or "",
        }
        by_name[bydel]["stories"].append(story)
        known[bydel].add(url_key)

    # Sorter hver bydel — nyeste først basert på date_iso (None/tom til slutt)
    for b in bydeler_list:
        b["stories"].sort(
            key=lambda s: (s.get("date_iso") or "0000-00-00"),
            reverse=True,
        )
    return bydeler_list


BYDELER = _ingest_cache(BYDELER)


# Enrich hver sak med lat/lng fra locations.py
def _enrich_locations(bydeler_list):
    if _loc is None:
        return bydeler_list
    for b in bydeler_list:
        for s in b["stories"]:
            s["bydel"] = b["name"]  # required by locations.resolve
            lat, lng, precise = _loc.resolve(s)
            s["lat"] = lat
            s["lng"] = lng
            s["location_precise"] = precise
    return bydeler_list


BYDELER = _enrich_locations(BYDELER)


COWORK_META = {
    "name": "Bydelsnytt Oslo",
    "schemaVersion": 1,
    "description": "Lokalnytt-dashboard for Oslo-bydeler. Data bakes inn i HTML-en og oppdateres daglig kl. 08:01 av en scheduled task som kjører WebSearch for hver bydel og oppdaterer artifact-et + publiserer til https://telboth.github.io/bydelsnytt/.",
}

STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: #fafaf9;
  color: #1a1a1a;
  line-height: 1.55;
}
.wrap { max-width: 920px; margin: 0 auto; }
header { margin-bottom: 20px; }
h1 { margin: 0 0 4px 0; font-size: 26px; font-weight: 600; }
.subtitle { color: #666; font-size: 13px; }
.byline { color: #777; font-size: 12px; margin-top: 4px; font-style: italic; }
.byline a { color: #1862a8; text-decoration: none; }
.byline a:hover { text-decoration: underline; }
.health-banner {
  background: #fff4e5;
  border: 1px solid #f5c27a;
  color: #663c00;
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}
.health-banner strong { color: #8a4a00; }
.health-banner ul { margin: 6px 0 0 0; padding-left: 20px; }
.health-banner li { margin: 2px 0; }
.controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e5e5e4;
  border-radius: 10px;
}
.controls label { display: block; font-size: 11px; color: #555; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 4px; }
.controls select, .controls input[type=search] {
  width: 100%; padding: 7px 10px; border: 1px solid #d4d4d1; border-radius: 6px;
  font-size: 14px; background: #fff;
}
.cat-chips {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
}
.cat-chip {
  display: inline-flex; align-items: center; gap: 4px; cursor: pointer;
  font-size: 12px; padding: 4px 9px; border-radius: 999px;
  border: 1px solid #d4d4d1; background: #fff; color: #555;
  user-select: none; transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.cat-chip input { margin: 0; cursor: pointer; display: none; }
.cat-chip::before {
  content: ""; width: 9px; height: 9px; border-radius: 50%;
  background: #5a6a80; display: inline-block; flex: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
}
.cat-chip[data-cat="politikk"]::before    { background: #8b27b3; }
.cat-chip[data-cat="skole"]::before       { background: #2b6fb5; }
.cat-chip[data-cat="idrett"]::before      { background: #2a8b4a; }
.cat-chip[data-cat="kultur"]::before      { background: #b8860b; }
.cat-chip[data-cat="trafikk"]::before     { background: #c14a1f; }
.cat-chip[data-cat="helse"]::before       { background: #b92674; }
.cat-chip[data-cat="naering"]::before     { background: #1f8b77; }
.cat-chip[data-cat="sikkerhet"]::before   { background: #b62323; }
.cat-chip[data-cat="arrangement"]::before { background: #b55a00; }
.cat-chip[data-cat="annet"]::before       { background: #5a6a80; }
.cat-chip.on { color: #fff; border-color: transparent; }
.cat-chip.on::before { box-shadow: inset 0 0 0 1.5px rgba(255,255,255,0.85); }
.cat-chip[data-cat="politikk"].on    { background: #8b27b3; }
.cat-chip[data-cat="skole"].on       { background: #2b6fb5; }
.cat-chip[data-cat="idrett"].on      { background: #2a8b4a; }
.cat-chip[data-cat="kultur"].on      { background: #b8860b; }
.cat-chip[data-cat="trafikk"].on     { background: #c14a1f; }
.cat-chip[data-cat="helse"].on       { background: #b92674; }
.cat-chip[data-cat="naering"].on     { background: #1f8b77; }
.cat-chip[data-cat="sikkerhet"].on   { background: #b62323; }
.cat-chip[data-cat="arrangement"].on { background: #b55a00; }
.cat-chip[data-cat="annet"].on       { background: #5a6a80; }
.cat-chip:hover { border-color: #999; }
.cat-chip.on:hover { filter: brightness(0.92); }
.cat-chip-all {
  font-size: 11px; color: #1862a8; background: transparent;
  border: none; padding: 3px 6px; cursor: pointer; text-decoration: underline;
}
.cat-chip-all:hover { color: #0d4a80; }
.bydel { margin-bottom: 28px; }
.bydel h2 {
  margin: 0 0 10px 0; font-size: 20px; border-bottom: 2px solid #1a1a1a;
  padding-bottom: 4px; display: flex; justify-content: space-between; align-items: baseline; gap: 10px;
}
.bydel h2 small { font-weight: 400; font-size: 12px; color: #777; }
.bydel h2 .h2-left { display: flex; align-items: baseline; gap: 8px; flex: 1; min-width: 0; }
.bydel h2 .h2-right { display: flex; align-items: center; gap: 8px; flex: none; }
.pin-bydel {
  background: transparent; border: none; padding: 2px 6px; cursor: pointer;
  font-size: 16px; line-height: 1; color: #bbb; border-radius: 4px;
  transition: color 0.12s, background 0.12s;
}
.pin-bydel:hover { color: #d4a017; background: #fff8e0; }
.pin-bydel.active { color: #d4a017; }
.pin-bydel.active:hover { color: #b8860b; }
.bydel.pinned {
  border-left: 4px solid #d4a017; padding-left: 14px;
  background: linear-gradient(90deg, #fff8e0 0%, transparent 60%);
}
.pinned-badge {
  display: inline-block; background: #d4a017; color: #fff;
  font-size: 10px; padding: 2px 8px; border-radius: 999px;
  text-transform: uppercase; letter-spacing: 0.4px; font-weight: 700;
  vertical-align: middle; margin-left: 4px;
}
.topp-saker {
  margin: 0 0 26px 0;
  padding: 16px 18px 14px;
  background: linear-gradient(180deg, #fffbee 0%, #fff 100%);
  border: 1px solid #e8d68a;
  border-radius: 12px;
}
.upcoming {
  margin: 0 0 26px 0;
  padding: 0;
  background: linear-gradient(180deg, #f1f8ff 0%, #fff 100%);
  border: 1px solid #b8d9f4;
  border-radius: 12px;
  overflow: hidden;
}
.upcoming > summary {
  padding: 14px 18px;
  cursor: pointer;
  list-style: none;
  font-size: 15px; font-weight: 700;
  color: #1862a8;
  text-transform: uppercase; letter-spacing: 0.6px;
  display: flex; align-items: baseline; gap: 10px;
}
.upcoming > summary::-webkit-details-marker { display: none; }
.upcoming > summary::before {
  content: "▶"; font-size: 10px; color: #1862a8;
  transform: translateY(-1px); transition: transform 0.15s;
}
.upcoming[open] > summary::before { transform: rotate(90deg) translateX(-1px); }
.upcoming-count {
  font-size: 11px; font-weight: 400; color: #4e80a8;
  text-transform: none; letter-spacing: 0;
}
.upcoming-body { padding: 4px 18px 16px 18px; }
.upcoming-group { margin-top: 10px; }
.upcoming-month {
  font-size: 12px; font-weight: 700; color: #365e82;
  text-transform: uppercase; letter-spacing: 0.4px;
  margin: 8px 0 6px 0; padding: 0; border: none;
}
.upcoming-list { list-style: none; margin: 0; padding: 0; }
.upcoming-item {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  padding: 6px 0; border-top: 1px solid #e8f0f8;
}
.upcoming-item:first-child { border-top: none; }
.upcoming-date {
  flex: 0 0 auto; min-width: 62px;
  font-size: 13px; font-weight: 700; color: #1862a8;
  font-variant-numeric: tabular-nums;
}
.upcoming-title { flex: 1 1 auto; color: #222; text-decoration: none; font-size: 14px; }
.upcoming-title:hover { text-decoration: underline; }
.upcoming-meta {
  flex: 0 0 auto; display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: #666;
}
.upcoming-bydel { color: #666; }
.upcoming-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 6px 0 10px 0; margin-bottom: 4px;
  border-bottom: 1px dashed #cfe0ef; font-size: 13px;
}
.upcoming-sync {
  display: flex; align-items: center; gap: 6px;
  font-weight: 600; color: #1862a8; cursor: pointer;
}
.upcoming-sync input { margin: 0; cursor: pointer; }
.upcoming-hint { color: #6b7f90; font-size: 12px; }
.upcoming-ics {
  flex: 0 0 auto; background: transparent; border: 1px solid #d9e4ef;
  border-radius: 4px; padding: 2px 7px; font-size: 13px; cursor: pointer;
  line-height: 1.2; color: #1862a8;
  transition: background 0.12s, border-color 0.12s;
}
.upcoming-ics:hover { background: #e8f2fa; border-color: #1862a8; }
.upcoming-item.hidden-filter, .upcoming-group.hidden-filter { display: none; }
a.story-ics {
  margin-right: 8px;
  background: transparent;
}
@media (max-width: 560px) {
  .upcoming-item { padding: 8px 0; }
  .upcoming-meta { flex-basis: 100%; padding-left: 72px; }
  .upcoming-hint { flex-basis: 100%; }
}
.topp-saker h2 {
  margin: 0 0 12px 0; font-size: 15px; font-weight: 700;
  color: #7a5e00; text-transform: uppercase; letter-spacing: 0.6px;
  border: none; padding: 0;
  display: flex; align-items: baseline; gap: 10px;
}
.topp-saker h2 small {
  font-size: 11px; font-weight: 400; color: #a08947;
  text-transform: none; letter-spacing: 0;
}
.topp-grid {
  display: grid; gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.topp-card {
  display: flex; gap: 10px; padding: 10px; text-decoration: none;
  background: #fff; border: 1px solid #efeadf; border-radius: 8px;
  transition: border-color 0.12s, transform 0.12s, box-shadow 0.12s;
  color: inherit; min-width: 0;
}
.topp-card:hover {
  border-color: #d4a017; transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(212,160,23,0.15);
}
.topp-thumb {
  flex: none; width: 72px; height: 54px; border-radius: 5px;
  overflow: hidden; background: #f0f0ee;
}
.topp-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.topp-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.topp-bydel {
  font-size: 10px; color: #7a5e00; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.topp-title {
  font-size: 13px; font-weight: 600; line-height: 1.35; color: #1a1a1a;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
}
.topp-meta {
  display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
  font-size: 11px; color: #888; margin-top: 2px;
}
.topp-src { font-style: italic; }
.topp-date { font-variant-numeric: tabular-nums; color: #aaa; }
.topp-pill {
  font-size: 9px; padding: 1px 6px; border-radius: 999px;
  background: #eef2f7; color: #33485f;
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600;
}
.topp-pill.skole { background: #e7f2ff; color: #1a4f8b; }
.topp-pill.politikk { background: #f3e8ff; color: #6b21a8; }
.topp-pill.idrett { background: #e8f6ec; color: #1f6d3a; }
.topp-pill.kultur { background: #fff3d9; color: #8a5a00; }
.topp-pill.trafikk { background: #ffe8e4; color: #9c2a12; }
.topp-pill.naering { background: #e4f3ef; color: #1f6b5c; }
.topp-pill.sikkerhet { background: #fce8e8; color: #9a1a1a; }
.topp-pill.helse { background: #ffeaf1; color: #9c1f5a; }
.topp-pill.arrangement { background: #fff0e4; color: #8a3a00; }
.story {
  background: #fff; border: 1px solid #e5e5e4; border-radius: 10px;
  padding: 14px 16px; margin-bottom: 10px;
}
.story.has-thumb {
  display: grid; grid-template-columns: 120px 1fr; gap: 14px;
  align-items: start;
}
.story .thumb {
  display: block; overflow: hidden; border-radius: 6px;
  aspect-ratio: 4 / 3; background: #f0f0ee;
}
.story .thumb img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  transition: transform 0.25s ease;
}
.story .thumb:hover img { transform: scale(1.04); }
.story .story-body { min-width: 0; }
@media (max-width: 540px) {
  .story.has-thumb { grid-template-columns: 88px 1fr; gap: 10px; }
}
.story h3 {
  margin: 0 0 6px 0; font-size: 15px; font-weight: 600;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.story .meta { font-size: 12px; color: #777; margin-bottom: 8px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.story .meta .source { font-weight: 500; color: #555; }
.story .meta .sep { color: #ccc; }
.story p { margin: 0 0 8px 0; font-size: 14px; line-height: 1.55; }
.story a.readmore { font-size: 13px; color: #1862a8; text-decoration: none; }
.story a.readmore:hover { text-decoration: underline; }
.story a.report {
  font-size: 11px; color: #aaa; text-decoration: none; margin-left: 10px;
  border-bottom: 1px dotted #ccc;
}
.story a.report:hover { color: #a04a4a; border-bottom-color: #a04a4a; }
.pill {
  display: inline-block; font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 999px;
  background: #eef2f7; color: #33485f; text-transform: uppercase; letter-spacing: 0.4px;
}
.pill.skole { background: #e7f2ff; color: #1a4f8b; }
.pill.politikk { background: #f3e8ff; color: #6b21a8; }
.pill.idrett { background: #e8f6ec; color: #1f6d3a; }
.pill.kultur { background: #fff3d9; color: #8a5a00; }
.pill.trafikk { background: #ffe8e4; color: #9c2a12; }
.pill.helse { background: #ffeaf1; color: #9c1f5a; }
.pill.naering { background: #e4f3ef; color: #1f6b5c; }
.pill.sikkerhet { background: #fce8e8; color: #9a1a1a; }
.pill.arrangement { background: #fff0e4; color: #8a3a00; }
.pill.annet { background: #eef2f7; color: #33485f; }
.news-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.6px;
  color: #0f5d2e; background: #d8f3dc; padding: 2px 7px;
  border-radius: 999px; text-transform: uppercase;
}
.news-badge::before {
  content: ""; width: 7px; height: 7px; border-radius: 50%;
  background: #1a9d4c; box-shadow: 0 0 0 2px rgba(26,157,76,0.2);
  display: inline-block;
}
.new-badge {
  display: inline-flex; align-items: center;
  font-size: 10px; font-weight: 700; letter-spacing: 0.6px;
  color: #6d1b7b; background: #f3e5f5; padding: 2px 7px;
  border-radius: 999px; text-transform: uppercase; margin-left: 6px;
}
.new-summary {
  margin-top: 6px; display: inline-block;
  font-size: 12px; color: #6d1b7b; background: #f3e5f5;
  padding: 3px 9px; border-radius: 12px; font-weight: 600;
}
.extra-sources {
  margin-top: 6px; font-size: 12px; color: #666;
}
.extra-sources a { color: #1862a8; text-decoration: none; }
.extra-sources a:hover { text-decoration: underline; }
.no-results {
  background: #fff; border: 1px dashed #d4d4d1; border-radius: 10px;
  padding: 20px; text-align: center; color: #888; font-style: italic;
}
#map {
  height: 340px; border-radius: 10px; margin-bottom: 20px;
  border: 1px solid #e5e5e4; background: #eee;
}
.map-legend {
  background: #fff; padding: 8px 10px; border-radius: 6px;
  font-size: 11px; line-height: 1.6; border: 1px solid #e5e5e4;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.map-legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.map-toggle {
  display: inline-flex; gap: 8px; align-items: center; margin-bottom: 12px;
  font-size: 13px; color: #555;
}
.map-toggle input { margin: 0; }
.leaflet-popup-content { font-size: 13px; line-height: 1.4; }
.leaflet-popup-content strong { display: block; margin-bottom: 4px; font-size: 13px; }
.leaflet-popup-content .popup-meta { color: #777; font-size: 11px; margin-top: 4px; }
footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #e5e5e4; color: #777; font-size: 12px; }
footer a { color: #1862a8; }
@media (max-width: 600px) {
  body { padding: 16px; }
}
/* Per-bruker skjul-kilde --------------------------------- */
.hide-src-btn {
  background: transparent;
  border: 1px solid #d6d6d6;
  color: #888;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: auto;
  flex-shrink: 0;
}
.hide-src-btn:hover {
  background: #f0f0f0;
  color: #1862a8;
  border-color: #b8d4eb;
}
.hide-src-btn.active {
  background: #fde6e6;
  color: #b32a2a;
  border-color: #f0c0c0;
}
.story .meta { flex-wrap: wrap; align-items: center; gap: 4px 8px; }
.story.is-hidden { display: none !important; }
.bydel.is-hidden { display: none !important; }
.upcoming-item.is-hidden { display: none !important; }

/* Preferanse-knapp i header */
.prefs-btn {
  background: transparent;
  border: 1px solid #cfcfcf;
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 13px;
  color: #444;
  margin-top: 6px;
}
.prefs-btn:hover { background: #f5f5f5; border-color: #888; }
.prefs-btn-count {
  display: inline-block;
  background: #b32a2a;
  color: #fff;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  margin-left: 4px;
}

/* Modal */
.prefs-modal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  display: none;
  align-items: center; justify-content: center;
  z-index: 9999;
}
.prefs-modal.open { display: flex; }
.prefs-modal-content {
  background: #fff;
  border-radius: 8px;
  padding: 20px 22px;
  max-width: 560px;
  width: calc(100% - 40px);
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}
.prefs-modal h3 { margin-top: 0; }
.prefs-modal h4 {
  margin: 18px 0 6px; font-size: 14px;
  color: #444; text-transform: uppercase; letter-spacing: 0.04em;
}
.prefs-modal-close {
  float: right; background: transparent; border: none;
  font-size: 22px; cursor: pointer; color: #888; line-height: 1;
}
.prefs-modal-close:hover { color: #b32a2a; }
.prefs-section { margin-bottom: 14px; }
.prefs-section-hint {
  color: #666; font-size: 13px; margin: 4px 0 8px;
}
.prefs-hidden-list { list-style: none; padding: 0; margin: 8px 0 12px; }
.prefs-hidden-list li {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border: 1px solid #eee; border-radius: 4px;
  margin-bottom: 6px; gap: 10px;
}
.prefs-hidden-list .src-name { font-weight: 500; }
.prefs-hidden-list .unhide {
  background: #1862a8; color: #fff; border: none;
  padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.prefs-hidden-list .unhide:hover { background: #154e85; }
.prefs-empty {
  color: #888; font-style: italic; padding: 8px 12px;
  background: #f8f8f8; border-radius: 4px; text-align: center;
  font-size: 13px;
}
.prefs-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 4px 12px;
  margin: 4px 0 6px;
}
.prefs-checkbox-grid label {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 6px; cursor: pointer; font-size: 13px;
  border-radius: 4px;
}
.prefs-checkbox-grid label:hover { background: #f5f5f5; }
.prefs-checkbox-grid input { margin: 0; }
.prefs-modal .clear-all {
  margin-top: 8px; background: transparent; border: 1px solid #b32a2a;
  color: #b32a2a; padding: 5px 10px; border-radius: 4px; cursor: pointer;
  font-size: 12px;
}
.prefs-modal .clear-all:hover { background: #b32a2a; color: #fff; }
/* --- Dark mode: variabler + override -------------------------- */
:root {
  --bn-bg: #fafafa;
  --bn-fg: #1a1a1a;
  --bn-card-bg: #fff;
  --bn-border: #e5e5e4;
  --bn-muted: #777;
  --bn-link: #1862a8;
  --bn-h2-bg: #ffffff;
  --bn-input-bg: #fff;
  --bn-input-border: #c8c8c8;
  --bn-modal-bg: #fff;
}
body.dark {
  --bn-bg: #15171a;
  --bn-fg: #e8e8e8;
  --bn-card-bg: #1f2227;
  --bn-border: #2c3035;
  --bn-muted: #999;
  --bn-link: #6ab2ff;
  --bn-h2-bg: #1f2227;
  --bn-input-bg: #1f2227;
  --bn-input-border: #3a3f47;
  --bn-modal-bg: #1f2227;
}
@media (prefers-color-scheme: dark) {
  body:not(.light) {
    --bn-bg: #15171a;
    --bn-fg: #e8e8e8;
    --bn-card-bg: #1f2227;
    --bn-border: #2c3035;
    --bn-muted: #999;
    --bn-link: #6ab2ff;
    --bn-h2-bg: #1f2227;
    --bn-input-bg: #1f2227;
    --bn-input-border: #3a3f47;
    --bn-modal-bg: #1f2227;
  }
}
body { background: var(--bn-bg); color: var(--bn-fg); }
.story { background: var(--bn-card-bg); border-color: var(--bn-border); }
.story p { color: var(--bn-fg); }
.story a.readmore { color: var(--bn-link); }
.story .meta .source { color: var(--bn-muted); }
section.bydel h2 { background: var(--bn-h2-bg); border-bottom-color: var(--bn-border); }
.controls select, .controls input[type="search"] {
  background: var(--bn-input-bg); color: var(--bn-fg);
  border-color: var(--bn-input-border);
}
.prefs-modal-content { background: var(--bn-modal-bg); color: var(--bn-fg); }
.about-modal-content p { color: var(--bn-fg); }
.upcoming-list, .topp-saker { background: var(--bn-card-bg); border-color: var(--bn-border); }
.upcoming-item, .topp-sak { border-color: var(--bn-border); }
footer { color: var(--bn-muted); border-top-color: var(--bn-border); }
.hide-src-btn { background: var(--bn-card-bg); color: var(--bn-muted); border-color: var(--bn-border); }
.prefs-btn { background: var(--bn-card-bg); color: var(--bn-fg); border-color: var(--bn-border); }
.prefs-empty { background: var(--bn-bg); color: var(--bn-muted); }
.prefs-checkbox-grid label { color: var(--bn-fg); }
.prefs-checkbox-grid label:hover { background: var(--bn-bg); }

/* --- SVG/CSS-fallback for saker uten bilde --------------- */
.thumb-fallback {
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; color: rgba(255,255,255,0.95); font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em;
  text-shadow: 0 1px 2px rgba(0,0,0,0.25);
}
.thumb-fallback.cat-politikk { background: linear-gradient(135deg,#a648c2,#6f1f88); }
.thumb-fallback.cat-skole    { background: linear-gradient(135deg,#3a8bd1,#1d5da3); }
.thumb-fallback.cat-idrett   { background: linear-gradient(135deg,#3aaa61,#1f7a3d); }
.thumb-fallback.cat-kultur   { background: linear-gradient(135deg,#d6a82c,#9b6c00); }
.thumb-fallback.cat-trafikk  { background: linear-gradient(135deg,#dc6a3e,#a13408); }
.thumb-fallback.cat-helse    { background: linear-gradient(135deg,#d23e90,#8e1452); }
.thumb-fallback.cat-naering  { background: linear-gradient(135deg,#2caa92,#10705e); }
.thumb-fallback.cat-sikkerhet { background: linear-gradient(135deg,#d23a3a,#8a0d0d); }
.thumb-fallback.cat-arrangement { background: linear-gradient(135deg,#e08533,#a14e00); }
.thumb-fallback.cat-annet    { background: linear-gradient(135deg,#7a8aa0,#4a5566); }

/* --- Sokeforslag-chips ------------------------------------ */
.search-suggestions {
  display: flex; flex-wrap: wrap; gap: 4px 6px; margin-top: 6px;
}
.search-suggestion {
  background: transparent; border: 1px solid var(--bn-border);
  color: var(--bn-muted); border-radius: 12px;
  padding: 2px 10px; font-size: 12px; cursor: pointer;
}
.search-suggestion:hover { background: var(--bn-card-bg); color: var(--bn-link); border-color: var(--bn-link); }
.search-suggestions-toggle {
  font-size: 11px; color: var(--bn-link); background: transparent;
  border: none; cursor: pointer; padding: 0; margin-left: 6px;
}

/* --- Theme toggle ----------------------------------------- */
.theme-btn {
  background: transparent; border: 1px solid var(--bn-border);
  border-radius: 6px; padding: 6px 10px; cursor: pointer;
  font-size: 13px; color: var(--bn-fg); margin-top: 6px;
}
.theme-btn:hover { background: var(--bn-card-bg); }
.about-modal-content p { line-height: 1.55; color: #333; margin: 8px 0 12px; }
.about-modal-content .about-link { color: #0a66c2; text-decoration: none; font-weight: 500; }
.about-modal-content .about-link:hover { text-decoration: underline; }
.about-modal-content ul.about-stack {
  list-style: disc; padding-left: 20px; margin: 4px 0 12px;
  color: #444; font-size: 14px;
}
.about-modal-content ul.about-stack li { margin: 2px 0; }
"""

SCRIPT = r"""
(function() {
  var selBydel = document.getElementById('bydel-filter');
  var catChips = document.getElementById('cat-chips');
  var catInputs = Array.from(document.querySelectorAll('.cat-chip-input'));
  var btnAll = document.getElementById('cat-chip-all');
  var btnNone = document.getElementById('cat-chip-none');
  var selPer   = document.getElementById('period-filter');
  var search   = document.getElementById('story-search');
  var searchCount = document.getElementById('search-count');
  var sections = Array.from(document.querySelectorAll('.bydel'));
  var emptyNote = document.getElementById('no-results');
  var TODAY = '__TODAY__';

  function getCheckedCats() {
    var s = {};
    catInputs.forEach(function(cb) {
      if (cb.checked) s[cb.value] = true;
    });
    return s;
  }

  function syncChipUi() {
    catInputs.forEach(function(cb) {
      var label = cb.closest('.cat-chip');
      if (!label) return;
      if (cb.checked) label.classList.add('on');
      else label.classList.remove('on');
    });
  }

  function inPastWindow(isoDate, n) {
    // True if isoDate is between (TODAY - n days) and TODAY, inclusive.
    // Future-dated items (events) are NOT matched — the period filter is
    // for recent/published content, not upcoming events.
    if (!isoDate) return false;
    if (isoDate > TODAY) return false;
    var d = new Date(TODAY + 'T00:00:00');
    d.setDate(d.getDate() - n);
    var cutoff = d.toISOString().slice(0, 10);
    return isoDate >= cutoff;
  }

  function inPastHours(isoTimestamp, hours) {
    // True if isoTimestamp (full ISO med tidssone) er innen siste N timer.
    // Bruker first_seen_iso (data-first-seen) for finere granularitet enn date_iso.
    if (!isoTimestamp) return false;
    var t = Date.parse(isoTimestamp);
    if (isNaN(t)) return false;
    var nowMs = Date.now();
    if (t > nowMs) return false;
    return (nowMs - t) <= hours * 3600 * 1000;
  }

  function storyMatches(story, cats, period, q) {
    var dataset = story.dataset;
    if (story.classList.contains('is-hidden')) return false;
    if (!cats[dataset.category]) return false;
    if (period === '12h' && !inPastHours(dataset.firstSeen, 12)) return false;
    if (period === '1d' && !inPastWindow(dataset.iso, 1)) return false;
    if (period === '7d' && !inPastWindow(dataset.iso, 7)) return false;
    if (period === '30d' && !inPastWindow(dataset.iso, 30)) return false;
    if (q) {
      var txt = story.innerText.toLowerCase();
      if (txt.indexOf(q) === -1) return false;
    }
    return true;
  }

  function apply() {
    var bv = selBydel ? selBydel.value : 'all';
    var cats = getCheckedCats();
    var pv = selPer.value;
    var q  = (search.value || '').toLowerCase().trim();
    var anyVisible = false;
    var totalShown = 0;

    sections.forEach(function(s) {
      var bydelName = s.dataset.name;
      if (bv !== 'all' && bv !== bydelName) { s.style.display = 'none'; return; }

      var stories = Array.from(s.querySelectorAll('.story'));
      var shownCount = 0;
      stories.forEach(function(st) {
        var show = storyMatches(st, cats, pv, q);
        st.style.display = show ? '' : 'none';
        if (show) shownCount++;
      });

      totalShown += shownCount;
      if (shownCount === 0) { s.style.display = 'none'; return; }
      s.style.display = '';
      anyVisible = true;

      var counter = s.querySelector('h2 small');
      if (counter) {
        counter.textContent = shownCount + ' sak' + (shownCount === 1 ? '' : 'er');
      }
    });

    if (emptyNote) emptyNote.style.display = anyVisible ? 'none' : '';
    if (searchCount) {
      if (q) {
        searchCount.textContent = totalShown + ' treff på \u00ab' + q + '\u00bb';
      } else {
        searchCount.textContent = '';
      }
    }
  }

  // --- Sokeforslag (tag-cloud chips) -----------------------------------
  try {
    var TAG_CLOUD = __TAG_CLOUD__;
    var ssBox = document.getElementById('search-suggestions');
    if (ssBox && Array.isArray(TAG_CLOUD) && TAG_CLOUD.length) {
      ssBox.hidden = false;
      ssBox.innerHTML = TAG_CLOUD.map(function(t) {
        return '<button type="button" class="search-suggestion" data-q="'
          + t.replace(/"/g, '&quot;') + '">' + t + '</button>';
      }).join('') + '<button type="button" class="search-suggestions-toggle" id="ssToggle">skjul</button>';
      ssBox.addEventListener('click', function(e) {
        var b = e.target.closest('.search-suggestion');
        if (b) { search.value = b.dataset.q; apply(); search.focus(); savePrefs(); return; }
        var t = e.target.closest('#ssToggle');
        if (t) { ssBox.hidden = true; }
      });
    }
  } catch (e) {}

  // --- Brukervalg huskes i localStorage -------------------------------
  var PREFS_KEY = 'bydelsnytt:filterState';
  function loadPrefs() {
    try {
      var raw = window.localStorage.getItem(PREFS_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) { return null; }
  }
  function savePrefs() {
    try {
      var state = {
        bydel: selBydel ? selBydel.value : null,
        period: selPer ? selPer.value : null,
        cats: catInputs.filter(function(cb) { return cb.checked; }).map(function(cb) { return cb.value; }),
        v: 1
      };
      window.localStorage.setItem(PREFS_KEY, JSON.stringify(state));
    } catch (e) { /* ignorerer */ }
  }
  (function restorePrefs() {
    var prefs = loadPrefs();
    if (!prefs) return;
    if (prefs.bydel && selBydel) {
      var found = false;
      for (var i = 0; i < selBydel.options.length; i++) {
        if (selBydel.options[i].value === prefs.bydel) { found = true; break; }
      }
      if (found) selBydel.value = prefs.bydel;
    }
    if (prefs.period && selPer) {
      for (var j = 0; j < selPer.options.length; j++) {
        if (selPer.options[j].value === prefs.period) { selPer.value = prefs.period; break; }
      }
    }
    if (prefs.cats && Array.isArray(prefs.cats)) {
      var set = {};
      prefs.cats.forEach(function(c) { set[c] = true; });
      catInputs.forEach(function(cb) { cb.checked = !!set[cb.value]; });
    }
  })();

  [selBydel, selPer].forEach(function(el) {
    if (el) el.addEventListener('change', function() { apply(); savePrefs(); });
  });
  catInputs.forEach(function(cb) {
    cb.addEventListener('change', function() { syncChipUi(); apply(); savePrefs(); });
  });
  if (btnAll) btnAll.addEventListener('click', function() {
    catInputs.forEach(function(cb) { cb.checked = true; });
    syncChipUi(); apply(); savePrefs();
  });
  if (btnNone) btnNone.addEventListener('click', function() {
    catInputs.forEach(function(cb) { cb.checked = false; });
    syncChipUi(); apply(); savePrefs();
  });
  search.addEventListener('input', apply);
  syncChipUi();
  apply();

  // --- "Mine bydeler": stjerne-toggle lagrer en LISTE av bydeler i localStorage.
  // Bakoverkompatibel med gammel single-bydel-noekkel.
  try {
    var MB_KEY = 'bydelsnytt:myBydel';        // legacy single
    var MBS_KEY = 'bydelsnytt:myBydeler';     // ny: array
    var myBydeler = {};
    try {
      var raw = window.localStorage.getItem(MBS_KEY);
      if (raw) {
        var arr = JSON.parse(raw);
        if (Array.isArray(arr)) arr.forEach(function(n) { if (n) myBydeler[n] = true; });
      }
    } catch (e) {}
    // Migrer legacy single-key
    try {
      if (Object.keys(myBydeler).length === 0) {
        var old = window.localStorage.getItem(MB_KEY);
        if (old) {
          myBydeler[old] = true;
          window.localStorage.setItem(MBS_KEY, JSON.stringify([old]));
        }
      }
    } catch (e) {}
    function persistMine() {
      try { window.localStorage.setItem(MBS_KEY, JSON.stringify(Object.keys(myBydeler))); } catch (e) {}
    }
    var main = document.querySelector('main');
    function applyPin() {
      // Markerer alle pin-bydeler i settet og floater dem oeverst i main.
      sections.forEach(function(s) {
        var btn = s.querySelector('.pin-bydel');
        if (myBydeler[s.dataset.name]) {
          s.classList.add('pinned');
          if (btn) { btn.classList.add('active'); btn.title = 'Fjern som mine bydeler'; }
        } else {
          s.classList.remove('pinned');
          if (btn) { btn.classList.remove('active'); btn.title = 'Legg til mine bydeler'; }
        }
      });
      // Flytt alle pinnede til toppen i opprinnelig rekkefoelge
      if (main) {
        var pinned = sections.filter(function(s) { return myBydeler[s.dataset.name]; });
        // Sett inn i revers slik at forste i listen blir oeverst
        pinned.reverse().forEach(function(s) {
          main.insertBefore(s, main.firstElementChild);
        });
      }
    }
    applyPin();

    document.querySelectorAll('.pin-bydel').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var name = btn.dataset.bydel;
        if (myBydeler[name]) delete myBydeler[name];
        else myBydeler[name] = true;
        persistMine();
        applyPin();
      });
    });
  } catch (e) {}

  // "Siden sist"-badge: merker saker som er dukket opp i cachen etter
  // brukerens forrige besoek. Personlig pr nettleser via localStorage.
  // Multi-bydel-aware: hvis brukeren har pinnet bydeler, vises "i dine bydeler".
  try {
    var KEY = 'bydelsnytt:lastVisit';
    var lastVisit = null;
    try { lastVisit = window.localStorage.getItem(KEY); } catch (e) {}

    // Hent pinnede bydeler (samme noekkel som multi-bydel-IIFE-en)
    var pinnedSet = {};
    try {
      var rawP = window.localStorage.getItem('bydelsnytt:myBydeler');
      if (rawP) {
        var arrP = JSON.parse(rawP);
        if (Array.isArray(arrP)) arrP.forEach(function(n) { if (n) pinnedSet[n] = true; });
      }
    } catch (e) {}
    var hasPinned = Object.keys(pinnedSet).length > 0;

    // Formater previous-visit som "21. apr" hvis tilgjengelig
    var MONTHS_NO = ['jan','feb','mar','apr','mai','jun','jul','aug','sep','okt','nov','des'];
    var sinceLabel = '';
    if (lastVisit) {
      var d = new Date(lastVisit);
      if (!isNaN(d.getTime())) {
        sinceLabel = d.getDate() + '. ' + MONTHS_NO[d.getMonth()];
      }
    }

    var stories = document.querySelectorAll('.story[data-first-seen]');
    var newTotal = 0;
    var newPinned = 0;
    stories.forEach(function(st) {
      var fs = st.dataset.firstSeen;
      if (!fs) return;
      if (lastVisit && fs <= lastVisit) return;
      var badge = st.querySelector('.new-badge');
      if (badge) {
        badge.textContent = sinceLabel ? ('Siden ' + sinceLabel) : 'Nytt';
        badge.hidden = false;
        // Skjul 24t-pillen for aa unngaa dobbel-badging
        var newsPill = st.querySelector('.news-badge');
        if (newsPill) newsPill.style.display = 'none';
      }
      newTotal++;
      // Sjekk om saken ligger i en pinnet bydel
      var section = st.closest('section[data-name]');
      if (section && pinnedSet[section.dataset.name]) {
        newPinned++;
      }
    });

    // Oppdater lastVisit etter 3s slik at brukeren rekker aa se badgene
    setTimeout(function() {
      try { window.localStorage.setItem(KEY, new Date().toISOString()); } catch (e) {}
    }, 3000);

    // Header-summary: foretrekker pinnede bydeler hvis brukeren har valgt noen
    var summaryText = '';
    if (hasPinned && newPinned > 0) {
      summaryText = 'Du har ' + newPinned + ' ny' + (newPinned === 1 ? '' : 'e')
        + ' sak' + (newPinned === 1 ? '' : 'er') + ' i dine bydeler';
      if (sinceLabel) summaryText += ' siden ' + sinceLabel;
    } else if (newTotal > 0) {
      summaryText = newTotal + ' ny' + (newTotal === 1 ? '' : 'e')
        + ' sak' + (newTotal === 1 ? '' : 'er');
      summaryText += sinceLabel ? (' siden ' + sinceLabel) : ' siden sist';
    }
    if (summaryText) {
      var tag = document.createElement('div');
      tag.className = 'new-summary';
      tag.textContent = summaryText;
      var header = document.querySelector('header');
      if (header) header.appendChild(tag);
    }
  } catch (e) { /* localStorage not available; silently skip */ }

  // --- "Hva skjer fremover": filter-synk med globale filtre + ICS-eksport ----
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function icsEsc(s) {
    return String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n')
      .replace(/,/g, '\\,').replace(/;/g, '\\;');
  }
  function buildIcs(title, urlStr, isoDate, description) {
    var d = isoDate.replace(/-/g, '');
    var dt = new Date();
    var stamp = dt.getUTCFullYear() +
      pad2(dt.getUTCMonth()+1) + pad2(dt.getUTCDate()) + 'T' +
      pad2(dt.getUTCHours()) + pad2(dt.getUTCMinutes()) + pad2(dt.getUTCSeconds()) + 'Z';
    var nextDay = new Date(isoDate + 'T00:00:00Z');
    nextDay.setUTCDate(nextDay.getUTCDate() + 1);
    var dEnd = nextDay.getUTCFullYear() +
      pad2(nextDay.getUTCMonth()+1) + pad2(nextDay.getUTCDate());
    return [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Bydelsnytt Oslo//telboth.github.io//NO',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      'UID:' + d + '-' + Math.random().toString(36).slice(2, 10) + '@bydelsnytt',
      'DTSTAMP:' + stamp,
      'DTSTART;VALUE=DATE:' + d,
      'DTEND;VALUE=DATE:' + dEnd,
      'SUMMARY:' + icsEsc(title),
      'DESCRIPTION:' + icsEsc(description || ''),
      'URL:' + icsEsc(urlStr || ''),
      'END:VEVENT',
      'END:VCALENDAR',
      ''
    ].join('\r\n');
  }
  function downloadIcs(filename, content) {
    var blob = new Blob([content], { type: 'text/calendar;charset=utf-8' });
    var u = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = u;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function() {
      document.body.removeChild(a);
      URL.revokeObjectURL(u);
    }, 100);
  }
  function slugFor(s) {
    return String(s || 'arrangement').toLowerCase()
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'arrangement';
  }

  try {
    var upcoming = document.getElementById('upcoming-events');
    var syncCb = document.getElementById('upcoming-sync-filter');
    if (upcoming && syncCb) {
      var upItems = upcoming.querySelectorAll('.upcoming-item');
      var upGroups = upcoming.querySelectorAll('.upcoming-group');
      var countEl = upcoming.querySelector('.upcoming-count');
      var totalN = parseInt((countEl && countEl.getAttribute('data-total')) || upItems.length, 10);

      function applyUpcomingFilter() {
        if (!syncCb.checked) {
          upItems.forEach(function(li) { li.classList.remove('hidden-filter'); });
          upGroups.forEach(function(g) { g.classList.remove('hidden-filter'); });
          if (countEl) countEl.textContent = totalN + ' arrangementer';
          return;
        }
        var bv = selBydel ? selBydel.value : 'all';
        var activeCats = {};
        catInputs.forEach(function(cb) { if (cb.checked) activeCats[cb.value] = true; });
        var anyCat = Object.keys(activeCats).length > 0;
        var visible = 0;
        upItems.forEach(function(li) {
          var bOk = (bv === 'all' || bv === li.dataset.bydel);
          var cOk = !anyCat || !!activeCats[li.dataset.category];
          if (bOk && cOk) {
            li.classList.remove('hidden-filter');
            visible++;
          } else {
            li.classList.add('hidden-filter');
          }
        });
        upGroups.forEach(function(g) {
          var any = g.querySelectorAll('.upcoming-item:not(.hidden-filter)').length;
          g.classList.toggle('hidden-filter', any === 0);
        });
        if (countEl) countEl.textContent = visible + ' arrangementer';
      }

      var UP_KEY = 'bydelsnytt:upcomingSync';
      try {
        var stored = window.localStorage.getItem(UP_KEY);
        if (stored === '1') syncCb.checked = true;
      } catch (e) {}
      syncCb.addEventListener('change', function() {
        try { window.localStorage.setItem(UP_KEY, syncCb.checked ? '1' : '0'); } catch (e) {}
        applyUpcomingFilter();
      });
      [selBydel, selPer].forEach(function(el) {
        if (el) el.addEventListener('change', applyUpcomingFilter);
      });
      catInputs.forEach(function(cb) {
        cb.addEventListener('change', applyUpcomingFilter);
      });
      if (btnAll) btnAll.addEventListener('click', applyUpcomingFilter);
      if (btnNone) btnNone.addEventListener('click', applyUpcomingFilter);
      applyUpcomingFilter();

      upcoming.querySelectorAll('.upcoming-ics').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          var li = btn.closest('.upcoming-item');
          if (!li) return;
          var title = li.dataset.title || '';
          var ev = li.dataset.eventDate || '';
          if (!ev) return;
          var link = li.querySelector('.upcoming-title');
          var urlStr = link ? link.href : '';
          var bydel = li.dataset.bydel || '';
          var desc = (bydel ? bydel + ' - ' : '') + 'Bydelsnytt Oslo\n' + urlStr;
          downloadIcs('bydelsnytt-' + slugFor(title) + '.ics', buildIcs(title, urlStr, ev, desc));
        });
      });
    }
  } catch (e) { /* no-op */ }

  // --- ICS-eksport på arrangement-saker i hovedfeeden -------------------------
  try {
    var today = new Date().toISOString().slice(0, 10);
    document.querySelectorAll('.story[data-event-date]').forEach(function(art) {
      var ev = art.dataset.eventDate || '';
      if (!ev || ev < today) return;
      if (art.querySelector('.story-ics')) return;
      var titleEl = art.querySelector('h3');
      var linkEl = art.querySelector('a.readmore');
      var title = (titleEl ? (titleEl.childNodes[0] ? titleEl.childNodes[0].textContent.trim() : '') : '') || 'Arrangement';
      var urlStr = linkEl ? linkEl.href : '';
      var btn = document.createElement('a');
      btn.href = '#';
      btn.className = 'report story-ics';
      btn.title = 'Legg til i kalender';
      btn.textContent = 'Kalender';
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        downloadIcs('bydelsnytt-' + slugFor(title) + '.ics',
          buildIcs(title, urlStr, ev, 'Bydelsnytt Oslo\n' + urlStr));
      });
      var reportBtn = art.querySelector('.report');
      if (reportBtn && reportBtn.parentNode) {
        reportBtn.parentNode.insertBefore(btn, reportBtn);
      } else {
        var body = art.querySelector('.story-body');
        if (body) body.appendChild(btn);
      }
    });
  } catch (e) { /* no-op */ }

  // --- Auto-scroll til min bydel ved innlasting -------------------------------
  try {
    var targetBydel = null;
    try { targetBydel = window.localStorage.getItem('bydelsnytt:myBydel'); } catch (e) {}
    if (!targetBydel) {
      try {
        var raw = window.localStorage.getItem('bydelsnytt:filterState');
        if (raw) {
          var obj = JSON.parse(raw);
          if (obj && obj.bydel && obj.bydel !== 'all') targetBydel = obj.bydel;
        }
      } catch (e) {}
    }
    if (targetBydel && !location.hash) {
      var target = document.querySelector('.bydel[data-name="' + targetBydel.replace(/"/g,'\\"') + '"]');
      if (target) {
        setTimeout(function() {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 250);
      }
    }
  } catch (e) {}
})();

(function() {
  // Per-bruker preferanser:
  //   bydelsnytt:hiddenSources    – source_id -> visningsnavn
  //   bydelsnytt:hiddenBydeler    – array av bydelsnavn
  //   bydelsnytt:hiddenCategories – array av kategori-slugs
  var HS_KEY = 'bydelsnytt:hiddenSources';
  var HB_KEY = 'bydelsnytt:hiddenBydeler';
  var HC_KEY = 'bydelsnytt:hiddenCategories';

  function loadMap(key) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw) return {};
      var arr = JSON.parse(raw);
      var map = {};
      if (Array.isArray(arr)) {
        arr.forEach(function(item) {
          if (typeof item === 'string') {
            map[item] = item;
          } else if (item && item.id) {
            map[item.id] = item.name || item.id;
          }
        });
      }
      return map;
    } catch (e) { return {}; }
  }

  function saveMap(key, map) {
    try {
      var arr = Object.keys(map).map(function(id) {
        return { id: id, name: map[id] };
      });
      window.localStorage.setItem(key, JSON.stringify(arr));
    } catch (e) {}
  }

  function loadSet(key) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw) return {};
      var arr = JSON.parse(raw);
      var set = {};
      if (Array.isArray(arr)) {
        arr.forEach(function(s) { if (typeof s === 'string') set[s] = true; });
      }
      return set;
    } catch (e) { return {}; }
  }

  function saveSet(key, set) {
    try {
      window.localStorage.setItem(key, JSON.stringify(Object.keys(set)));
    } catch (e) {}
  }

  var hiddenSources = loadMap(HS_KEY);
  var hiddenBydeler = loadSet(HB_KEY);
  var hiddenCats = loadSet(HC_KEY);

  // Bygg modal-DOM
  var modal = document.createElement('div');
  modal.className = 'prefs-modal';
  modal.innerHTML = ''
    + '<div class="prefs-modal-content">'
    + '  <button class="prefs-modal-close" aria-label="Lukk">&times;</button>'
    + '  <h3>Preferanser</h3>'
    + '  <div class="prefs-section">'
    + '    <h4>Skjulte kilder</h4>'
    + '    <p class="prefs-section-hint">Saker fra disse kildene vises ikke. Bruk &laquo;Vis igjen&raquo; for &aring; reaktivere.</p>'
    + '    <ul class="prefs-hidden-list" id="prefs-hidden-list"></ul>'
    + '  </div>'
    + '  <div class="prefs-section">'
    + '    <h4>Vis bydeler</h4>'
    + '    <p class="prefs-section-hint">Hak av bydelene du vil se. Alle er p&aring; som standard.</p>'
    + '    <div class="prefs-checkbox-grid" id="prefs-bydel-grid"></div>'
    + '  </div>'
    + '  <div class="prefs-section">'
    + '    <h4>Vis kategorier</h4>'
    + '    <p class="prefs-section-hint">Hak av kategoriene du vil se. Alle er p&aring; som standard.</p>'
    + '    <div class="prefs-checkbox-grid" id="prefs-cat-grid"></div>'
    + '  </div>'
    + '  <button class="clear-all" id="prefs-clear-all">Fjern alle preferanser</button>'
    + '</div>';
  document.body.appendChild(modal);

  var modalList = modal.querySelector('#prefs-hidden-list');
  var bydelGrid = modal.querySelector('#prefs-bydel-grid');
  var catGrid   = modal.querySelector('#prefs-cat-grid');
  var clearAllBtn = modal.querySelector('#prefs-clear-all');

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c];
    });
  }
  function escapeAttr(s) { return escapeHtml(s); }

  // Hent komplette lister av bydeler og kategorier fra DOM
  function discoverBydeler() {
    var seen = {};
    var out = [];
    document.querySelectorAll('.bydel[data-name]').forEach(function(el) {
      var n = el.dataset.name;
      if (n && !seen[n]) { seen[n] = true; out.push(n); }
    });
    out.sort(function(a, b) { return a.localeCompare(b, 'no'); });
    return out;
  }

  function discoverCategories() {
    // Bruk eksisterende kategori-chips som autoritativ kilde for label/slug
    var out = [];
    var seen = {};
    document.querySelectorAll('.cat-chip-input').forEach(function(cb) {
      var slug = cb.value;
      var label = cb.parentElement ? (cb.parentElement.textContent || '').trim() : slug;
      if (slug && !seen[slug]) {
        seen[slug] = true;
        out.push({ slug: slug, label: label || slug });
      }
    });
    return out;
  }

  function renderModalList() {
    var ids = Object.keys(hiddenSources);
    if (ids.length === 0) {
      modalList.innerHTML = '<li class="prefs-empty">Ingen kilder er skjult</li>';
    } else {
      modalList.innerHTML = ids.map(function(id) {
        var name = hiddenSources[id] || id;
        return '<li>'
          + '<span class="src-name">' + escapeHtml(name) + '</span>'
          + '<button class="unhide" data-src-id="' + escapeAttr(id) + '">Vis igjen</button>'
          + '</li>';
      }).join('');
    }
  }

  function renderBydelGrid() {
    var bs = discoverBydeler();
    bydelGrid.innerHTML = bs.map(function(name) {
      // Checked = synlig (dvs IKKE i hiddenBydeler). Default: alt paa.
      var checked = hiddenBydeler[name] ? '' : ' checked';
      return '<label><input type="checkbox" class="prefs-bydel-cb" value="'
        + escapeAttr(name) + '"' + checked + '> ' + escapeHtml(name) + '</label>';
    }).join('');
  }

  function renderCatGrid() {
    var cs = discoverCategories();
    catGrid.innerHTML = cs.map(function(c) {
      // Checked = synlig (dvs IKKE i hiddenCats). Default: alt paa.
      var checked = hiddenCats[c.slug] ? '' : ' checked';
      return '<label><input type="checkbox" class="prefs-cat-cb" value="'
        + escapeAttr(c.slug) + '"' + checked + '> ' + escapeHtml(c.label) + '</label>';
    }).join('');
  }

  function applyHidden() {
    // Stories: skjul hvis kilde, bydel eller kategori er skjult
    var stories = document.querySelectorAll('.story');
    stories.forEach(function(st) {
      var srcId = st.dataset.sourceId;
      var cat   = st.dataset.category;
      // Bydel hentes fra parent <section class="bydel">
      var section = st.closest('.bydel');
      var bydel = section ? section.dataset.name : '';
      var hide = false;
      if (srcId && hiddenSources[srcId]) hide = true;
      else if (cat && hiddenCats[cat]) hide = true;
      else if (bydel && hiddenBydeler[bydel]) hide = true;
      if (hide) st.classList.add('is-hidden');
      else st.classList.remove('is-hidden');
    });

    // Skjul hele bydel-seksjoner (gjelder alle visninger – ogsaa naar
    // bydel-filteret er paa "alle"). Det gir samme effekt for "min bydel"-
    // markering og topp-saker som filtrerer mot DOM.
    document.querySelectorAll('.bydel[data-name]').forEach(function(sec) {
      if (hiddenBydeler[sec.dataset.name]) sec.classList.add('is-hidden');
      else sec.classList.remove('is-hidden');
    });

    // Hva skjer fremover-elementer
    document.querySelectorAll('.upcoming-item').forEach(function(li) {
      var b = li.dataset.bydel;
      var c = li.dataset.category;
      var hide = (b && hiddenBydeler[b]) || (c && hiddenCats[c]);
      if (hide) li.classList.add('is-hidden');
      else li.classList.remove('is-hidden');
    });

    // Trigger re-apply av eksisterende filter for tellere/no-results
    var sel = document.getElementById('bydel-filter');
    if (sel) sel.dispatchEvent(new Event('change'));
    updatePrefsButton();
  }

  function updatePrefsButton() {
    var btn = document.getElementById('open-prefs-btn');
    if (!btn) return;
    var n = Object.keys(hiddenSources).length
          + Object.keys(hiddenBydeler).length
          + Object.keys(hiddenCats).length;
    var countEl = btn.querySelector('.prefs-btn-count');
    if (n === 0) {
      if (countEl) countEl.remove();
    } else {
      if (countEl) {
        countEl.textContent = n;
      } else {
        var s = document.createElement('span');
        s.className = 'prefs-btn-count';
        s.textContent = n;
        btn.appendChild(s);
      }
    }
  }

  // Per-saks skjul-knapp
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.hide-src-btn');
    if (btn) {
      e.preventDefault();
      var id = btn.dataset.srcId;
      var name = btn.dataset.srcName || id;
      if (!id) return;
      var label = name || id;
      var ok = window.confirm('Skjul alle saker fra "' + label + '"?\n\nDu kan reaktivere kilden via "Preferanser" \u00f8verst.');
      if (!ok) return;
      hiddenSources[id] = name;
      saveMap(HS_KEY, hiddenSources);
      applyHidden();
      return;
    }
    // Reaktiver kilde
    var unhideBtn = e.target.closest('.unhide');
    if (unhideBtn) {
      var rid = unhideBtn.dataset.srcId;
      if (rid && hiddenSources[rid]) {
        delete hiddenSources[rid];
        saveMap(HS_KEY, hiddenSources);
        renderModalList();
        applyHidden();
      }
      return;
    }
    // Aapne modal
    var openBtn = e.target.closest('#open-prefs-btn');
    if (openBtn) {
      e.preventDefault();
      renderModalList();
      renderBydelGrid();
      renderCatGrid();
      modal.classList.add('open');
      return;
    }
    // Lukk modal
    if (e.target === modal || e.target.closest('.prefs-modal-close')) {
      modal.classList.remove('open');
      return;
    }
  });

  // Bydel-checkboxes
  bydelGrid.addEventListener('change', function(e) {
    var cb = e.target.closest('.prefs-bydel-cb');
    if (!cb) return;
    var name = cb.value;
    // cb.checked = synlig => fjern fra hidden-set
    if (cb.checked) delete hiddenBydeler[name];
    else hiddenBydeler[name] = true;
    saveSet(HB_KEY, hiddenBydeler);
    applyHidden();
  });

  // Kategori-checkboxes
  catGrid.addEventListener('change', function(e) {
    var cb = e.target.closest('.prefs-cat-cb');
    if (!cb) return;
    var slug = cb.value;
    // cb.checked = synlig => fjern fra hidden-set
    if (cb.checked) delete hiddenCats[slug];
    else hiddenCats[slug] = true;
    saveSet(HC_KEY, hiddenCats);
    applyHidden();
  });

  clearAllBtn.addEventListener('click', function() {
    if (!window.confirm('Fjern alle skjulte kilder, bydeler og kategorier?')) return;
    hiddenSources = {};
    hiddenBydeler = {};
    hiddenCats = {};
    saveMap(HS_KEY, hiddenSources);
    saveSet(HB_KEY, hiddenBydeler);
    saveSet(HC_KEY, hiddenCats);
    renderModalList();
    renderBydelGrid();
    renderCatGrid();
    applyHidden();
  });

  // Lukk paa Esc
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('open')) {
      modal.classList.remove('open');
    }
  });

  // Initial filtrering ved sidelasting
  applyHidden();
  updatePrefsButton();
})();


(function() {
  var TKEY = 'bydelsnytt:theme';
  var btn = document.getElementById('theme-toggle');
  if (!btn) return;
  function setIcon() {
    var isDark = document.body.classList.contains('dark');
    btn.innerHTML = isDark ? '&#9728;&#65038;' : '&#9790;&#65038;';
    btn.title = isDark ? 'Bytt til lyst tema' : 'Bytt til morkt tema';
  }
  // Initial: legacy + system preference
  try {
    var saved = window.localStorage.getItem(TKEY);
    if (saved === 'dark') document.body.classList.add('dark');
    else if (saved === 'light') document.body.classList.add('light');
  } catch (e) {}
  setIcon();
  btn.addEventListener('click', function() {
    var isDark = document.body.classList.contains('dark');
    document.body.classList.remove('dark');
    document.body.classList.remove('light');
    if (isDark) document.body.classList.add('light');
    else document.body.classList.add('dark');
    try { window.localStorage.setItem(TKEY, isDark ? 'light' : 'dark'); } catch (e) {}
    setIcon();
  });
})();

(function() {
  // Om denne siden-modal.
  var modal = document.createElement('div');
  modal.className = 'prefs-modal about-modal';
  modal.innerHTML = ''
    + '<div class="prefs-modal-content about-modal-content">'
    + '  <button class="prefs-modal-close" aria-label="Lukk">&times;</button>'
    + '  <h3>Om denne siden</h3>'
    + '  <p>Bydelsnytt Oslo samler nyheter og hendelser fra alle 15 bydeler i Oslo p\u00e5 ett sted. '
    + 'Sakene hentes automatisk fra lokalaviser, bydelssider, kommunens kunngj\u00f8ringer, idrettslag, '
    + 'kulturhus og kalendertjenester. En liten algoritme klassifiserer dem i kategorier som politikk, '
    + 'skole, idrett, trafikk og arrangement, og pinner dem p\u00e5 kartet n\u00e5r vi kjenner stedet.</p>'
    + '  <p>Pipelinen kj\u00f8rer hver morgen og oppdaterer feeden. Du kan filtrere p\u00e5 bydel, kategori og '
    + 'periode, s\u00f8ke i innholdet, og bruke <strong>Preferanser</strong> til \u00e5 skjule kilder, bydeler '
    + 'eller kategorier du ikke vil se. Valgene dine lagres lokalt i nettleseren.</p>'
    + '  <p>Denne websiden er laget av Thomas Elboth. Den er et lite hobbyprosjekt for \u00e5 se hva en '
    + 'kan utvikle ved hjelp av moderne kodeverkt\u00f8y. '
    + '<a class="about-link" href="' + 'https://www.linkedin.com/in/thomaselboth/' + '" target="_blank" rel="noopener">Se min LinkedIn-profil</a>.</p>'
    + '  <p style="font-size:13px;color:#666;">Kildekoden ligger \u00e5pent p\u00e5 '
    + '<a class="about-link" href="https://github.com/telboth/bydelsnytt" target="_blank" rel="noopener">GitHub</a>. '
    + 'Funnet feil eller noe som mangler? Send en e-post til '
    + '<a class="about-link" href="mailto:t.elboth@gmail.com">t.elboth@gmail.com</a>.</p>'
    + '</div>';
  document.body.appendChild(modal);

  document.addEventListener('click', function(e) {
    var openBtn = e.target.closest('#open-about-btn');
    if (openBtn) {
      e.preventDefault();
      modal.classList.add('open');
      return;
    }
    if (e.target === modal || (modal.classList.contains('open') && e.target.closest('.about-modal .prefs-modal-close'))) {
      modal.classList.remove('open');
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('open')) {
      modal.classList.remove('open');
    }
  });
})();
"""

MAP_SCRIPT = r"""
(function() {
  if (typeof L === 'undefined' || !window.MAP_POINTS) return;
  var points = window.MAP_POINTS;
  var mapEl = document.getElementById('map');
  var toggle = document.getElementById('map-toggle');

  var COLORS = {
    politikk: '#8b27b3', skole: '#2b6fb5', idrett: '#2a8b4a',
    kultur: '#b8860b', trafikk: '#c14a1f', helse: '#b92674',
    naering: '#1f8b77', sikkerhet: '#b62323', arrangement: '#b55a00',
    annet: '#5a6a80'
  };

  var map = L.map('map', { zoomControl: true }).setView([59.925, 10.76], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);

  var grouped = {};
  points.forEach(function(p) {
    var key = p.lat.toFixed(3) + ',' + p.lng.toFixed(3);
    (grouped[key] = grouped[key] || []).push(p);
  });

  var allMarkers = [];
  Object.keys(grouped).forEach(function(k) {
    var pts = grouped[k];
    pts.forEach(function(p, idx) {
      var offsetLat = p.lat, offsetLng = p.lng;
      if (pts.length > 1) {
        var angle = (2 * Math.PI / pts.length) * idx;
        offsetLat += Math.cos(angle) * 0.0015;
        offsetLng += Math.sin(angle) * 0.0022;
      }
      var color = COLORS[p.category] || COLORS.annet;
      var marker = L.circleMarker([offsetLat, offsetLng], {
        radius: p.precise ? 7 : 5,
        color: '#fff', weight: 2, fillColor: color, fillOpacity: 0.9
      });
      var popup = '<strong>' + escapeHtml(p.title) + '</strong>' +
                  '<div class="popup-meta">' + escapeHtml(p.bydel) + ' &middot; ' +
                  escapeHtml(p.source) + '</div>' +
                  '<div style="margin-top:6px;"><a href="#' + p.id + '">Gå til sak &rarr;</a></div>';
      marker.bindPopup(popup);
      marker._bydelsnytt = p;
      marker.addTo(map);
      allMarkers.push(marker);
    });
  });

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"]/g, function(c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }

  function getCheckedCats() {
    var s = {};
    document.querySelectorAll('.cat-chip-input').forEach(function(cb) {
      if (cb.checked) s[cb.value] = true;
    });
    return s;
  }

  function refreshMap() {
    var elBydel = document.getElementById('bydel-filter');
    var selBydel = elBydel ? elBydel.value : 'all';
    var cats = getCheckedCats();
    allMarkers.forEach(function(m) {
      var p = m._bydelsnytt;
      var show = (selBydel === 'all' || selBydel === p.bydel) &&
                 !!cats[p.category];
      if (show) { if (!map.hasLayer(m)) m.addTo(map); }
      else      { if (map.hasLayer(m)) map.removeLayer(m); }
    });
  }

  ['bydel-filter', 'period-filter'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('change', refreshMap);
  });
  document.querySelectorAll('.cat-chip-input').forEach(function(cb) {
    cb.addEventListener('change', refreshMap);
  });
  var catAll = document.getElementById('cat-chip-all');
  var catNone = document.getElementById('cat-chip-none');
  if (catAll) catAll.addEventListener('click', refreshMap);
  if (catNone) catNone.addEventListener('click', refreshMap);

  refreshMap();
  var visible = allMarkers.filter(function(m) { return map.hasLayer(m); });
  if (visible.length) {
    var grp = L.featureGroup(visible);
    map.fitBounds(grp.getBounds().pad(0.1));
  }

  if (toggle) {
    toggle.addEventListener('change', function() {
      mapEl.style.display = toggle.checked ? '' : 'none';
      if (toggle.checked) setTimeout(function() { map.invalidateSize(); }, 50);
    });
  }
})();
"""


def esc(s): return html.escape(s, quote=True)


def _story_id(story, bydel_name):
    import hashlib
    h = hashlib.sha1()
    h.update((bydel_name + "|" + (story.get("url") or "") + "|" + story.get("title", "")).encode())
    return "s-" + h.hexdigest()[:10]


REPORT_EMAIL = "thomas.elboth@xlent.no"


def _report_mailto(story, bydel_name, sid):
    """Bygger en mailto-URL med prefilled emne og body for feilrapport."""
    title = story.get("title", "")
    url = story.get("url", "") or ""
    source = story.get("source", "") or ""
    subject = f"Bydelsnytt-feil: {title[:80]}"
    body = (
        f"Sak-ID: {sid}\n"
        f"Bydel: {bydel_name}\n"
        f"Kilde: {source}\n"
        f"Tittel: {title}\n"
        f"URL: {url}\n\n"
        f"Hva er feil?\n"
        f"(f.eks. dødt bilde, feil bydel, feil kategori, bør skjules)\n"
    )
    q = urllib.parse.urlencode(
        {"subject": subject, "body": body}, quote_via=urllib.parse.quote
    )
    return f"mailto:{REPORT_EMAIL}?{q}"


def _build_tag_cloud(stories: list[dict], n: int = 14) -> list[str]:
    """Bygg en lite tag-sky av populaere tokens fra titler + sammendrag.

    Returnerer topp-N enkeltord (laereord, lengde >= 4) som kan brukes som
    klikkbare sokeforslag. Skipper stoppord og generelle ord som ikke er
    nyttige som sok.
    """
    import re
    from collections import Counter
    stop = set("""
        ikke skal vil kommer kommet bare bare ogsa hadde noe noen mer
        eller fra med pa pa det den dette dette dem som har vart vaert
        gjort har har bare for til til fra fra ved av av en ei et og
        eller men hva hvor naar nar man hun han ham henne det det dem
        deg deg meg vi du oss seg hverandre vil ville skulle kunne
        bydel bydelen oslos oslo kommune sak saker viser bli blir blitt
        her det dette nytt nye gamle stor store store nylig flere mange
        siden samme andre deres begge alle alt etter foer for for rundt
        gjennom mellom over under uten ved siden sammen over over tre
        ser ser sa siden side site nyhetsside nyheter nytt nye gammel
        nylig tidligere senere snart akkurat samme andre annet alt
    """.split())
    rx = re.compile(r"[A-Za-zÀ-ÿ]+", re.UNICODE)
    counter = Counter()
    for s in stories:
        text = (s.get("title", "") + " " + s.get("summary", "")).lower()
        for tok in rx.findall(text):
            if len(tok) < 4 or tok in stop:
                continue
            counter[tok] += 1
    # Filtrer ut altfor vanlige (>30% av saker = ord-hver-tredje-sak)
    threshold = max(2, len(stories) // 3)
    out = []
    for tok, c in counter.most_common(80):
        if c > threshold:
            continue
        out.append(tok)
        if len(out) >= n:
            break
    return out


def render_story(story, bydel_name=""):
    fresh = is_fresh(story)
    badge = ' <span class="news-badge">news</span>' if fresh else ""
    cat = story.get("category", "annet")
    cat_label = CAT_LABEL.get(cat, "Annet")
    date_iso = story.get("date_iso") or ""
    first_seen = story.get("first_seen_iso") or ""
    sid = _story_id(story, bydel_name)
    story["_html_id"] = sid
    src_id_attr = story.get("source_id") or ""
    src_name = story.get("source") or ""
    if src_id_attr:
        hide_btn_html = (
            f'<button class="hide-src-btn" type="button" '
            f'aria-label="Skjul saker fra denne kilden" '
            f'title="Skjul saker fra {esc(src_name)}" '
            f'data-src-id="{esc(src_id_attr)}" '
            f'data-src-name="{esc(src_name)}">&#9881;</button>'
        )
    else:
        hide_btn_html = ""
    # Ekstra kilder (kryss-kilde-dedup) under meta-raden
    extra_html = ""
    extras = story.get("extra_sources") or []
    if extras:
        links = []
        for ex in extras:
            name = ex.get("source") or ex.get("source_id") or ""
            url = ex.get("url") or ""
            if not name or not url:
                continue
            links.append(
                f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(name)}</a>'
            )
        if links:
            extra_html = (
                '<div class="extra-sources">Ogsaa omtalt i: '
                + ", ".join(links) + "</div>"
            )
    img_url = story.get("image_url") or ""
    thumb_html = ""
    if img_url:
        thumb_html = (
            f'<a class="thumb" href="{esc(story["url"])}" target="_blank" '
            f'rel="noopener" aria-hidden="true">'
            f'<img src="{esc(img_url)}" loading="lazy" alt="" '
            f'onerror="var a=this.closest(&quot;article&quot;);'
            f'if(a)a.querySelector(&quot;.thumb&quot;).outerHTML=a.dataset.fallback||&quot;&quot;;'
            f'"></a>'
        )
    else:
        # CSS-gradient fallback med bydelsinitialer
        bydel_init = (bydel_name[:1] if bydel_name else "?").upper()
        thumb_html = (
            f'<a class="thumb thumb-fallback cat-{esc(cat)}" href="{esc(story["url"])}" '
            f'target="_blank" rel="noopener" aria-hidden="true">'
            f'<span>{esc(bydel_init)}</span></a>'
        )
    event_date = story.get("event_date") or ""
    return f"""
    <article id="{sid}" class="story has-thumb" data-category="{esc(cat)}" data-iso="{esc(date_iso)}" data-first-seen="{esc(first_seen)}" data-event-date="{esc(event_date)}" data-source-id="{esc(src_id_attr)}" data-source-name="{esc(src_name)}">
      {thumb_html}
      <div class="story-body">
        <h3>{esc(story['title'])}{badge}<span class="new-badge" hidden>NYTT</span></h3>
        <div class="meta">
          <span class="source">{esc(story['source'])}</span>
          <span class="sep">&middot;</span>
          <span>{esc(story['date'])}</span>
          <span class="sep">&middot;</span>
          <span class="pill {esc(cat)}">{esc(cat_label)}</span>
          {hide_btn_html}
        </div>
        <p>{esc(story['summary'])}</p>
        <a class="readmore" href="{esc(story['url'])}" target="_blank" rel="noopener">Les mer &rarr;</a>
        <a class="report" href="{esc(_report_mailto(story, bydel_name, sid))}" title="Rapporter problem med denne saken">Rapporter</a>
        {extra_html}
      </div>
    </article>"""


def render_bydel(b):
    count = len(b['stories'])
    stories_html = "\n".join(render_story(s, b['name']) for s in b['stories'])
    return f"""
  <section class="bydel" data-name="{esc(b['name'])}">
    <h2>
      <span class="h2-left">{esc(b['name'])} <small>{count} sak{'er' if count != 1 else ''}</small></span>
      <span class="h2-right">
        <button class="pin-bydel" type="button" data-bydel="{esc(b['name'])}" title="Sett som min bydel" aria-label="Sett som min bydel">&#9733;</button>
      </span>
    </h2>
    {stories_html}
  </section>"""


# --- Topp-saker --------------------------------------------------------------
# Scorer hver sak ut fra ferskhet, kilde-kvalitet, kategori-relevans og
# bydels-sjeldenhet (saker i underdekte bydeler scorer hoeyere). Plukker
# topp-5 med diversitetskrav: hver bydel kan kun vaere representert en gang,
# hver kategori maksimalt to ganger.

_TOPP_CAT_WEIGHT = {
    "sikkerhet": 1.3, "trafikk": 1.15, "politikk": 1.05, "helse": 1.0,
    "skole": 0.95, "naering": 0.85, "kultur": 0.75, "idrett": 0.75,
    "arrangement": 0.55, "annet": 0.45,
}
_TOPP_SOURCE_WEIGHT = {
    "oslo-kommune-aktuelt": 1.15, "groruddalen": 1.05, "nrk-oslo-viken": 1.15,
    "politi-oslo": 1.2, "vartoslo": 1.05, "dagsavisen": 1.0, "vegvesen": 1.05,
    "ruter-avvik": 1.0, "ruter-sx": 1.0, "e24": 0.95, "tu": 0.95,
    "oslomet": 0.9, "uio": 0.95, "bi-business-review": 0.9, "kampanje": 0.9,
    "deichman-aktuelt": 0.9, "kondis": 0.85, "nho": 0.85,
    "skeid": 0.7, "vif-fotball": 0.75, "boeler-if": 0.7, "iltry": 0.7,
    "reddit-oslo": 0.6, "events": 0.55, "oslo-arrangement": 0.6,
}

def _topp_score(story, bydel_name, today_iso, bydel_activity):
    iso = (story.get("date_iso") or "")[:10]
    if not iso or iso > today_iso:
        return 0.0
    # Ferskhet: 1.0 i dag, 0.85 i gaar, 0.6 to dager siden, 0.35 siste uke, 0.1 ellers
    try:
        from datetime import date as _date
        d_story = _date.fromisoformat(iso)
        d_today = _date.fromisoformat(today_iso)
        days_ago = (d_today - d_story).days
    except ValueError:
        return 0.0
    if days_ago < 0:
        return 0.0
    if days_ago == 0:
        freshness = 1.0
    elif days_ago == 1:
        freshness = 0.85
    elif days_ago <= 3:
        freshness = 0.55
    elif days_ago <= 7:
        freshness = 0.3
    else:
        return 0.0  # eldre enn en uke teller ikke som topp

    cat = story.get("category") or "annet"
    cat_w = _TOPP_CAT_WEIGHT.get(cat, 0.45)

    src_id = story.get("source_id") or ""
    src_w = _TOPP_SOURCE_WEIGHT.get(src_id, 0.75)

    # Bydels-sjeldenhetsbonus: saker i underdekte bydeler scorer hoeyere
    n = bydel_activity.get(bydel_name, 1)
    scarcity = 1.0 + max(0.0, (12 - n) / 24.0)  # opp til ~1.5x for sjeldne

    # Tittel-kvalitet: lengre, mer spesifikk tittel gir liten bonus
    title_len = len(story.get("title") or "")
    title_bonus = min(title_len / 80.0, 1.0) * 0.15 + 0.85

    return freshness * cat_w * src_w * scarcity * title_bonus


def _pick_top_stories(bydeler_list, today_iso, n=5):
    # Bygg bydel-aktivitet (saker siste 7 dager per bydel) for scarcity-bonus
    from datetime import date as _date, timedelta as _td
    try:
        cutoff = (_date.fromisoformat(today_iso) - _td(days=7)).isoformat()
    except ValueError:
        cutoff = "0000-00-00"
    bydel_activity = {}
    for b in bydeler_list:
        count = sum(
            1 for s in b["stories"]
            if (s.get("date_iso") or "")[:10] >= cutoff
        )
        bydel_activity[b["name"]] = count

    candidates = []
    for b in bydeler_list:
        bname = b["name"]
        for s in b["stories"]:
            score = _topp_score(s, bname, today_iso, bydel_activity)
            if score > 0:
                candidates.append((score, bname, s))

    candidates.sort(key=lambda t: -t[0])

    picked = []
    used_bydeler = set()
    used_cats = {}
    for score, bname, s in candidates:
        if bname in used_bydeler:
            continue
        cat = s.get("category") or "annet"
        if used_cats.get(cat, 0) >= 2:
            continue
        picked.append((score, bname, s))
        used_bydeler.add(bname)
        used_cats[cat] = used_cats.get(cat, 0) + 1
        if len(picked) >= n:
            break
    return picked


def _render_topp_saker(bydeler_list, today_iso):
    top = _pick_top_stories(bydeler_list, today_iso, n=5)
    if not top:
        return ""
    cards = []
    for score, bname, s in top:
        title = esc(s.get("title", "") or "(uten tittel)")
        url = esc(s.get("url", "") or "#")
        source = esc(s.get("source", "") or "")
        cat = s.get("category") or "annet"
        cat_label = esc(CAT_LABEL.get(cat, cat))
        date_iso = esc((s.get("date_iso") or "")[:10])
        img_url = s.get("image_url") or ""
        img_html = ""
        if img_url:
            img_html = (
                f'<span class="topp-thumb" aria-hidden="true">'
                f'<img src="{esc(img_url)}" loading="lazy" alt="" '
                f'onerror="this.parentElement.style.display=&quot;none&quot;"></span>'
            )
        cards.append(
            f'<a class="topp-card" href="{url}" target="_blank" rel="noopener">'
            f'{img_html}'
            f'<span class="topp-body">'
            f'<span class="topp-bydel">{esc(bname)}</span>'
            f'<span class="topp-title">{title}</span>'
            f'<span class="topp-meta">'
            f'<span class="topp-src">{source}</span>'
            f'<span class="topp-pill {esc(cat)}">{cat_label}</span>'
            f'<span class="topp-date">{date_iso}</span>'
            f'</span>'
            f'</span>'
            f'</a>'
        )
    return (
        '<section class="topp-saker" aria-label="Topp saker i dag">'
        '<h2>Topp saker i dag <small>utvalgt av algoritmen</small></h2>'
        '<div class="topp-grid">'
        + "".join(cards)
        + '</div>'
        '</section>'
    )


def _render_upcoming_events(bydeler_list, today_iso):
    """Rendre en 'Hva skjer fremover'-seksjon med arrangementer som har
    event_date i fremtiden. Sorteres etter event_date stigende. Saker
    med passert event_date tas ikke med. Rendres som <details> slik at
    den er sammenklappet som default."""
    upcoming = []
    for b in bydeler_list:
        bname = b["name"]
        for s in b["stories"]:
            ev = s.get("event_date") or ""
            if not ev or ev <= today_iso:
                continue
            upcoming.append((ev, bname, s))
    if not upcoming:
        return ""
    upcoming.sort(key=lambda t: (t[0], t[1]))

    from datetime import date as _date
    month_no = {
        1: "Januar", 2: "Februar", 3: "Mars", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    groups: dict[str, list] = {}
    group_order: list[str] = []
    for ev, bname, s in upcoming:
        try:
            d = _date.fromisoformat(ev)
            key = f"{month_no[d.month]} {d.year}"
        except ValueError:
            key = ev[:7]
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append((ev, bname, s))

    parts = []
    for key in group_order:
        items = []
        for ev, bname, s in groups[key]:
            try:
                d = _date.fromisoformat(ev)
                day_label = f"{d.day}. {month_no[d.month].lower()[:3]}."
            except ValueError:
                day_label = ev[5:]
            cat = s.get("category") or "annet"
            cat_label = esc(CAT_LABEL.get(cat, cat))
            title = esc(s.get("title", "") or "(uten tittel)")
            url = esc(s.get("url", "") or "#")
            items.append(
                f'<li class="upcoming-item" data-bydel="{esc(bname)}" data-category="{esc(cat)}" data-event-date="{esc(ev)}" data-title="{esc(s.get("title","") or "")}">'
                f'<span class="upcoming-date">{esc(day_label)}</span>'
                f'<a class="upcoming-title" href="{url}" target="_blank" rel="noopener">{title}</a>'
                f'<button type="button" class="upcoming-ics" title="Legg til i kalender" aria-label="Legg til i kalender">&#128197;</button>'
                f'<span class="upcoming-meta">'
                f'<span class="pill {esc(cat)}">{cat_label}</span>'
                f'<span class="upcoming-bydel">{esc(bname)}</span>'
                f'</span>'
                f'</li>'
            )
        parts.append(
            f'<div class="upcoming-group" data-month="{esc(key)}">'
            f'<h3 class="upcoming-month">{esc(key)}</h3>'
            f'<ul class="upcoming-list">{"".join(items)}</ul>'
            f'</div>'
        )

    toolbar = (
        '<div class="upcoming-toolbar">'
        '<label class="upcoming-sync"><input type="checkbox" id="upcoming-sync-filter">'
        ' Synk med filter ovenfor</label>'
        '<span class="upcoming-hint">Skjuler arrangementer som ikke matcher bydel og kategori</span>'
        '</div>'
    )
    return (
        '<details class="upcoming" id="upcoming-events">'
        f'<summary>Hva skjer fremover <span class="upcoming-count" data-total="{len(upcoming)}">{len(upcoming)} arrangementer</span></summary>'
        f'<div class="upcoming-body">{toolbar}{"".join(parts)}</div>'
        '</details>'
    )


def _build_map_data(bydeler_list):
    data = []
    for b in bydeler_list:
        for s in b["stories"]:
            if not s.get("lat") or not s.get("lng"):
                continue
            data.append({
                "id": s.get("_html_id") or _story_id(s, b["name"]),
                "lat": s["lat"],
                "lng": s["lng"],
                "bydel": b["name"],
                "title": s.get("title", ""),
                "category": s.get("category", "annet"),
                "source": s.get("source", ""),
                "precise": bool(s.get("location_precise")),
            })
    return data


def _render_health_banner() -> str:
    """Returner HTML-banner hvis noen kilder har vaert stale > 7 dager.
    Baserer seg paa source_health.json laget av pipeline/run.py."""
    if _health is None:
        return ""
    try:
        data = _health.load()
    except Exception as e:
        print(f"[build] kunne ikke lese source_health.json: {e}", file=sys.stderr)
        return ""
    stale = _health.stale_sources(data)
    if not stale:
        return ""
    lis = []
    for s in stale:
        last = s.get("last_success_iso") or "aldri"
        if last != "aldri":
            last = last[:10]
        lis.append(
            f"<li><strong>{esc(s['name'])}</strong> "
            f"(siste suksess: {esc(last)})</li>"
        )
    return (
        '<div class="health-banner">'
        '<strong>Kildehelse:</strong> '
        f'{len(stale)} kilde{"" if len(stale)==1 else "r"} har ikke levert saker '
        'paa en uke. Sjekk om feedene fremdeles fungerer:'
        f'<ul>{"".join(lis)}</ul>'
        '</div>'
    )


def render_page(include_cowork_meta):
    meta_tag = ""
    if include_cowork_meta:
        meta_tag = f'<script type="application/json" id="cowork-artifact-meta">\n{json.dumps(COWORK_META, ensure_ascii=False, indent=2)}\n</script>\n'

    cat_chips = []
    for key, label in CATEGORIES:
        cat_chips.append(
            f'<label class="cat-chip on" data-cat="{esc(key)}">'
            f'<input type="checkbox" class="cat-chip-input" value="{esc(key)}" checked>'
            f'{esc(label)}</label>'
        )
    cat_chips.append('<button type="button" class="cat-chip-all" id="cat-chip-all">Velg alle</button>')
    cat_chips.append('<button type="button" class="cat-chip-all" id="cat-chip-none">Fjern alle</button>')
    cat_chips_html = "\n      ".join(cat_chips)

    period_options_html = """<option value="all">Alle datoer</option>
      <option value="12h">Siste 12 timer</option>
      <option value="1d">Siste 24 timer</option>
      <option value="7d">Siste uke</option>
      <option value="30d">Siste måned</option>"""

    # Render stories first to populate _html_id, then build map points
    body = "\n".join(render_bydel(b) for b in BYDELER)
    map_points_json = json.dumps(_build_map_data(BYDELER), ensure_ascii=False)

    total_stories = sum(len(b['stories']) for b in BYDELER)
    fresh_count = sum(1 for b in BYDELER for s in b['stories'] if is_fresh(s))

    _all_for_cloud = [s for b in BYDELER for s in b["stories"]]
    script_js = SCRIPT.replace("__TODAY__", TODAY_ISO).replace("__TAG_CLOUD__", json.dumps(_build_tag_cloud(_all_for_cloud), ensure_ascii=False))
    health_banner_html = _render_health_banner()
    topp_saker_html = _render_topp_saker(BYDELER, TODAY_ISO)
    upcoming_html = _render_upcoming_events(BYDELER, TODAY_ISO)


    return f"""<!DOCTYPE html>
{meta_tag}<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bydelsnytt Oslo &ndash; {esc(DATE_NO)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#1862a8">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Bydelsnytt Oslo</h1>
  <div class="subtitle">{esc(DATE_NO)} &middot; {total_stories} saker fra 15 bydeler &middot; {fresh_count} fersk{'' if fresh_count == 1 else 'e'} siste 24 timer</div>
  <button id="open-prefs-btn" class="prefs-btn" type="button" title="Administrer preferanser (skjul kilder, bydeler, kategorier)">&#9881; Preferanser</button>
  <button id="open-about-btn" class="prefs-btn" type="button" title="Om denne siden">&#9432; Om denne siden</button>
  <button id="theme-toggle" class="theme-btn" type="button" title="Bytt mellom lyst og morkt tema" aria-label="Bytt tema">&#9728;&#65038;</button>
</header>
{health_banner_html}
<div class="controls">
  <div style="grid-column: 1 / -1;">
    <label>Kategori <span style="font-weight:400;text-transform:none;color:#777;">(klikk for å vise/skjule)</span></label>
    <div class="cat-chips" id="cat-chips">
      {cat_chips_html}
    </div>
  </div>
  <div>
    <label for="period-filter">Periode</label>
    <select id="period-filter">
      {period_options_html}
    </select>
  </div>
  <div style="grid-column: 1 / -1;">
    <label for="story-search">Søk <span id="search-count" style="font-weight:400;text-transform:none;color:#1862a8;margin-left:6px;"></span></label>
    <input id="story-search" type="search" placeholder="Filtrer i innholdet (f.eks. &laquo;trikk&raquo;, &laquo;bibliotek&raquo;, &laquo;17. mai&raquo;)&hellip;">
    <div id="search-suggestions" class="search-suggestions" hidden></div>
  </div>
</div>
{topp_saker_html}
{upcoming_html}
<label class="map-toggle"><input type="checkbox" id="map-toggle" checked> Vis kart</label>
<div id="map"></div>
<main>{body}
<div id="no-results" class="no-results" style="display:none;">Ingen saker matcher filtrene dine. Prøv å huke av flere kategorier eller endre Bydel/Periode.</div>
</main>
<footer>
  Sist oppdatert {esc(TIMESTAMP_ISO)}. Oppdateres daglig 08:01.
  Kilde: automatiske RSS-feeds (Oslo kommune, Groruddalen, NRK Oslo/Viken) + håndkuratert innhold fra skoler og idrettslag.
  <br>
  <a href="feed.xml">RSS-feed</a> · <a href="weekly/">Ukesarkiv</a> · Live: <a href="https://telboth.github.io/bydelsnytt/">telboth.github.io/bydelsnytt</a>.
  <span class="visit-counter" id="visit-counter" style="margin-left: 8px; padding-left: 8px; border-left: 1px solid #ddd; color: #888;">Besøk: <span id="visit-count">…</span></span>
</footer>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>window.MAP_POINTS = {map_points_json};</script>
<script>{script_js}</script>
<script>{MAP_SCRIPT}</script>
<script>
(function() {{
  var el = document.getElementById('visit-count');
  if (!el) return;
  // Abacus: counts each pageview but throttles per-visitor; no tracking cookies, no PII.
  fetch('https://abacus.jasoncameron.dev/hit/bydelsnytt/visits')
    .then(function(r) {{ return r.ok ? r.json() : null; }})
    .then(function(d) {{
      if (d && typeof d.value === 'number') {{
        el.textContent = d.value.toLocaleString('nb-NO');
      }} else {{
        el.parentNode.style.display = 'none';
      }}
    }})
    .catch(function() {{ el.parentNode.style.display = 'none'; }});
}})();
</script>
<script>
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', function() {{
    navigator.serviceWorker.register('sw.js').catch(function(){{}});
  }});
}}
</script>
</body>
</html>
"""


out_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(out_dir, exist_ok=True)

with open(f"{out_dir}/bydelsnytt_artifact.html", "w", encoding="utf-8") as f:
    f.write(render_page(include_cowork_meta=True))

with open(f"{out_dir}/bydelsnytt_publish.html", "w", encoding="utf-8") as f:
    f.write(render_page(include_cowork_meta=False))

print("artifact bytes:", os.path.getsize(f"{out_dir}/bydelsnytt_artifact.html"))
print("publish  bytes:", os.path.getsize(f"{out_dir}/bydelsnytt_publish.html"))
