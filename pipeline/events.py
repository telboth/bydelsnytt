"""Kuratert seed-liste av Oslo-arrangementer: loep, sykkelritt, skirenn,
fotballkamper, festivaler, kulturarrangementer.

Data kommer fra aarlige, tilbakevendende arrangementer. Datoer er beste estimat
basert paa typisk helg-moenster (f.eks. Oslo Maraton = 3. loerdag i september).
Sjekk arranger-siden for eksakt dato/tid.

Hver event er et dict som matcher RawStory.to_dict()-formatet. Pipeline-run
merge-er disse paa lik linje med RSS/HTML-scrapede saker, og classify-modulen
respekterer kategorien vi setter her.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def _event_id(url: str, title: str) -> str:
    h = hashlib.sha1()
    h.update(url.lower().strip().encode())
    h.update(b"|")
    h.update(title.lower().strip().encode())
    return h.hexdigest()[:16]


# Tuples: (tittel, url, bydel, date_iso, category, summary)
EVENTS = [
    # --- Loep / mosjonsloep -------------------------------------------------
    ("Sentrumsloepet 2026",
     "https://www.sentrumslopet.no/",
     "Frogner", "2026-04-25", "idrett",
     "Oslos klassiske bygateloepet gjennom sentrum. 10 km med start og maal "
     "paa Raadhusplassen. Ett av Norges stoerste byloep, arrangeres aarlig "
     "siste loerdag i april."),

    ("Holmenkollstafetten 2026",
     "https://holmenkollstafetten.no/",
     "Frogner", "2026-05-09", "idrett",
     "Aarets store stafettlopp med 15 etapper i sentrum. 2. loerdag i mai. "
     "Trekker over 40.000 loepere fra skoler, bedrifter og klubber."),

    ("Styrkeproeven 2026 (Trondheim-Oslo)",
     "https://www.styrkeproven.no/",
     "Frogner", "2026-06-20", "idrett",
     "Nordens stoerste sykkelritt paa landevei. 540 km fra Trondheim til "
     "Oslo; maal i Frognerparken. Arrangeres tredje helg i juni."),

    ("Oslo Grand Prix 2026 (sykkel)",
     "https://www.oslograndprix.no/",
     "Frogner", "2026-06-13", "idrett",
     "Kriteriumritt i Oslo sentrum. Profesjonelle og mosjonist-ritt samme "
     "dag. Ruten gaar gjennom Frogner og sentrum."),

    ("Oslo Triathlon 2026",
     "https://oslotri.com/",
     "Nordre Aker", "2026-08-22", "idrett",
     "Byens stoerste triatlon med svoemming i Sognsvann, sykkel og loep "
     "rundt Nordmarka/Nordre Aker. Sprint-, olympisk og halv-distanse."),

    ("Norway Cup 2026",
     "https://www.norwaycup.no/",
     "Gamle Oslo", "2026-07-26", "idrett",
     "Verdens stoerste fotballturnering for barn og ungdom paa "
     "Ekebergsletta. En ukes spill med over 2000 lag fra hele verden."),

    ("Grefsenkollen opp 2026",
     "https://www.grefsenkollenopp.no/",
     "Nordre Aker", "2026-09-05", "idrett",
     "Motbakkeloep fra Storo til Grefsenkollen restaurant. 4,7 km med "
     "478 hm stigning. Klassiker hver hoest."),

    ("Oslos bratteste 2026 (tidligere Tryvann opp)",
     "https://oslosbratteste.no/",
     "Vestre Aker", "2026-09-12", "idrett",
     "Motbakkeloep fra Frognerseteren til Tryvannstaarnet. Kort men bratt, "
     "ca 3,5 km. Tidligere kjent som Tryvann opp, omdoept til Oslos bratteste."),

    ("Oslo Maraton 2026",
     "https://www.oslomaraton.no/",
     "Frogner", "2026-09-19", "idrett",
     "Norges stoerste maraton. Maratonloep, halvmaraton, 10 km og barneloep "
     "gjennom sentrum, Frogner, Bjoervika og Groenerloekka. Start/maal paa "
     "Raadhusplassen."),

    ("Bygdoymila 2026",
     "https://www.bygdoymila.no/",
     "Frogner", "2026-10-18", "idrett",
     "Terrengloep rundt Bygdoey. Klassisk halvmaraton paa stier gjennom "
     "kongsgaarden og Bygdoey-skogen. Aarlig i oktober."),

    # --- Kultur / festivaler ------------------------------------------------
    ("17. mai-feiringen 2026",
     "https://www.oslo.kommune.no/17-mai/",
     "Frogner", "2026-05-17", "kultur",
     "Barnetoget gaar opp Karl Johan forbi Slottet der Kongefamilien hilser. "
     "Hovedarrangementer i Slottsparken og langs paraderuten."),

    ("Musikkfest Oslo 2026",
     "https://www.musikkfest.no/",
     "St. Hanshaugen", "2026-06-20", "kultur",
     "Gratis musikkfestival med over 1000 artister paa scenes i hele "
     "sentrum. Arrangeres loerdag naermest sankthans hver sommer."),

    ("Oslo Pride Parade 2026",
     "https://www.oslopride.no/",
     "Frogner", "2026-06-27", "kultur",
     "Paraden gaar fra Groenland til Raadhusplassen. Pride Park arrangeres "
     "samme uke i Spikersuppa og Kontraskjaeret."),

    ("Oeyafestivalen 2026",
     "https://www.oyafestivalen.no/",
     "Gamle Oslo", "2026-08-04", "kultur",
     "Norges stoerste urbane musikkfestival i Toeyenparken. Fire dager med "
     "nasjonale og internasjonale hovedartister. Klimanoeytral og "
     "oekologisk profilert."),

    ("Oslo Jazzfestival 2026",
     "https://www.oslojazz.no/",
     "St. Hanshaugen", "2026-08-17", "kultur",
     "En uke med jazz paa scener rundt Oslo sentrum: Nasjonal jazzscene, "
     "Rockefeller, Kulturkirken Jakob og flere utearenaer."),

    ("Kulturnatt Oslo 2026",
     "https://kulturnatt.oslo.no/",
     "St. Hanshaugen", "2026-09-11", "kultur",
     "En kveld der over 150 kulturinstitusjoner holder aapent gratis. "
     "Museer, teatre, gallerier og bibliotek i hele sentrum."),

    ("Inferno Metal Festival 2026",
     "https://infernofestival.net/",
     "St. Hanshaugen", "2026-04-29", "kultur",
     "Internasjonal metalfestival over 4 dager paa Rockefeller og John "
     "Dee. Paaskehoelt med norske og internasjonale hovedartister."),

    # --- Skirenn (vinter 2027) ----------------------------------------------
    ("Holmenkollmarsjen 2027",
     "https://www.holmenkollmarsjen.no/",
     "Vestre Aker", "2027-03-06", "idrett",
     "Turrenn paa 42 km eller 21 km i Nordmarka. Start og maal ved "
     "Holmenkollen skistadion. Forste loerdag i mars."),

    ("FIS World Cup Holmenkollen 2027",
     "https://www.holmenkollen-skifest.no/",
     "Vestre Aker", "2027-03-13", "idrett",
     "Verdenscup-helg i langrenn, hopp og kombinert paa Holmenkollen. "
     "Over 100.000 tilskuere over tre dager."),

    ("Sognsvann rundt medsols 2027",
     "https://www.sognsvannrundt.no/",
     "Nordre Aker", "2027-02-07", "idrett",
     "Turrenn rundt Sognsvann og inn i Nordmarka. Tre distanser: 5 km, "
     "10 km og 20 km. Klassisk familie-skirenn."),


    # --- Loppemarkeder (vaarloppis 2026) -----------------------------------
    ("Ris skoles loppemarked 2026",
     "https://ris.osloskolen.no/for-elever-og-foresatte/fau/loppemarked/",
     "Vestre Aker", "2026-05-02", "arrangement",
     "Aarlig vaarloppis arrangert av FAU paa Ris skole. Inntekter gaar til "
     "elevaktiviteter. Innlevering fredag, salg loerdag. Klassiker paa "
     "vestkanten."),

    ("Nordberg skoles loppemarked 2026",
     "https://nordberg.osloskolen.no/",
     "Nordre Aker", "2026-05-09", "arrangement",
     "FAU-loppis paa Nordberg skole med klaer, boeker, sportsutstyr og "
     "kjoekkenting. Salg loerdag 10-14 i gymsalen."),

    ("T\u00e5sen skoles loppemarked 2026",
     "https://tasen.osloskolen.no/",
     "Nordre Aker", "2026-04-25", "arrangement",
     "Tradisjonsrik vaarloppis paa T\u00e5sen skole. FAU dekker overskudd "
     "til skoleturer. Innlevering torsdag, salg loerdag 10-13."),

    ("Vahl skoles loppemarked 2026",
     "https://vahl.osloskolen.no/",
     "Gamle Oslo", "2026-05-16", "arrangement",
     "Vaarloppis paa Vahl skole paa Gr\u00f8nland. Mangfoldig loppis med "
     "fokus paa baerekraftig gjenbruk i lokalmiljoeet."),

    ("Ellingsrudaasen skoles h\u00f8stloppis 2026",
     "https://ellingsrudasen.osloskolen.no/",
     "Alna", "2026-09-26", "arrangement",
     "H\u00f8st-loppemarked i Furuset-omraadet. Innsamling i forkant, stort "
     "utvalg av ting til hjem og fritid."),

    # --- Speidergrupper (lokale aktiviteter) -------------------------------
    ("Ris speidergruppe - ukentlige m\u00f8ter",
     "https://www.rispeiderne.no/",
     "Vestre Aker", "2026-04-22", "arrangement",
     "Ris speidergruppe har ukentlige m\u00f8ter for bevere, smaaspeidere, "
     "speidere og rovere. M\u00f8tested: Speiderhuset ved Ris stasjon. "
     "Aktiviteter: friluftsliv, patruljearbeid, hiking i Nordmarka."),

    ("Nordstrand speidergruppe - aktiviteter v\u00e5r 2026",
     "https://www.nordstrandspeiderne.no/",
     "Nordstrand", "2026-04-24", "arrangement",
     "Nordstrand speidergruppe - en av Oslos stoerste. Ukentlige m\u00f8ter "
     "paa Tallberget. V\u00e5rens hoeydepunkt: patruljetur i Oestmarka "
     "og pinseleir for alle aldersgrupper."),

    ("Sagene speidergruppe - aktiviteter",
     "https://sagenespeiderne.no/",
     "Sagene", "2026-04-23", "arrangement",
     "Sagene speidergruppe samler speidere fra Sagene, Torshov og "
     "Bjoelsen. M\u00f8ter ved Bjoerkelunden. Fokus paa byspeiding og "
     "tur til Oslomarka."),

    ("Grorud speidergruppe",
     "https://norges-speiderforbund.no/gruppe/grorud/",
     "Grorud", "2026-04-25", "arrangement",
     "Grorud speidergruppe m\u00f8tes ukentlig ved Grorud kirke. "
     "Aktiviteter spenner fra friluftsliv i Lillomarka til sosiale "
     "prosjekter i bydelen."),

    ("Holmlia speidergruppe",
     "https://norges-speiderforbund.no/gruppe/holmlia/",
     "S\u00f8ndre Nordstrand", "2026-04-22", "arrangement",
     "Holmlia speidergruppe - aktiv gruppe i et flerkulturelt nabolag. "
     "M\u00f8ter i Holmlia-omraadet med fokus paa integrering og "
     "friluftsliv i Oestmarka."),

    ("Gr\u00fcnerl\u00f8kka speidergruppe",
     "https://norges-speiderforbund.no/gruppe/grunerlokka/",
     "Gr\u00fcnerl\u00f8kka", "2026-04-28", "arrangement",
     "Gr\u00fcnerl\u00f8kka speidergruppe - byspeidere paa oestkanten. "
     "M\u00f8ter paa Sofienberg. Kombinerer urbane aktiviteter med "
     "turer til Marka."),

    # --- Lions-klubber i Oslo ---------------------------------------------
    ("Lions Club Oslo Nordstrand - aktiviteter",
     "https://www.lions.no/oslonordstrand/",
     "Nordstrand", "2026-05-05", "arrangement",
     "Lions Club Oslo Nordstrand stoetter lokalt ungdomsarbeid og "
     "humanitaere prosjekter. Maanedlige m\u00f8ter + aarlig juleaksjon "
     "og innsamling til Lions Tulipan."),

    ("Lions Club Oslo/Vestre Aker",
     "https://www.lions.no/oslovestreaker/",
     "Vestre Aker", "2026-05-12", "arrangement",
     "Lions Club Oslo/Vestre Aker - aktive siden 1965. Arrangerer "
     "julemarked, tulipan-aksjon og stoetter eldrearbeid i bydelen."),

    ("Lions Club Oslo/Groruddalen",
     "https://www.lions.no/oslogroruddalen/",
     "Grorud", "2026-05-19", "arrangement",
     "Lions Club Oslo/Groruddalen drifter aarlig loppemarked og "
     "tulipan-aksjon. Midler gaar til ungdomsaktiviteter og "
     "humanitaert arbeid lokalt i Groruddalen."),

    ("Lions Club Oslo/Gamle Oslo",
     "https://www.lions.no/oslogamleoslo/",
     "Gamle Oslo", "2026-05-26", "arrangement",
     "Lions Club Oslo/Gamle Oslo stoetter mangfoldige lokale "
     "prosjekter paa Toeyen og Gr\u00f8nland. Aktive i Tulipanaksjonen "
     "hver vaar og i julehjelp hver desember."),

    # --- Kinopremierer / kinosaler ----------------------------------------
    ("Vega Scene - aktuelle filmer",
     "https://www.vegascene.no/program",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Vega Scene paa Hausmannsplass viser arthouse-film, kortfilm og "
     "dokumentarer. Kinotek-profil med norske og internasjonale "
     "premierer, Q&A og filmklubber."),

    ("Saga Kino - storfilmer vaaren 2026",
     "https://www.oslokino.no/kino/saga/",
     "Frogner", "2026-04-22", "kultur",
     "Saga Kino ved Klingenberg viser storfilmer paa stor leredet. "
     "Aktuell vaarsesong med norske og amerikanske premierer."),

    ("Colosseum Kino - IMAX og premierer",
     "https://www.oslokino.no/kino/colosseum/",
     "Frogner", "2026-04-22", "kultur",
     "Colosseum paa Majorstua - Nordens stoerste kinosal. Storfilm-"
     "premierer, IMAX-visninger og spesialarrangementer. Klassisk "
     "kinopalass bygd i 1928."),

    ("Gimle Kino - arthouse og repertoire",
     "https://www.oslokino.no/kino/gimle/",
     "Frogner", "2026-04-22", "kultur",
     "Gimle Kino paa Bygdoey all\u00e9 viser kuraterte filmer og "
     "klassikere i koselige lokaler. Premiere for utvalgte norske og "
     "europeiske filmer."),

    # --- Teater-forestillinger --------------------------------------------
    ("Nationaltheatret - aktuelt program",
     "https://www.nationaltheatret.no/forestillinger",
     "Frogner", "2026-04-22", "kultur",
     "Nationaltheatret spiller klassikere og samtidsdrama paa "
     "Hovedscenen og Amfiscenen. Oslos hovedteater med norsk og "
     "internasjonal dramatikk."),

    ("Det Norske Teatret - nynorsk scene",
     "https://www.detnorsketeatret.no/repertoar",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Det Norske Teatret paa Kristian IV's gate - Norges nynorsk-"
     "scene. Spiller egne produksjoner og gjestende ensembler. "
     "Inkluderende program for unge."),

    ("Oslo Nye Teater",
     "https://www.oslonye.no/repertoar",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Oslo Nye Teater paa Centralteatret + Hovedscenen. Bredt "
     "repertoar med familie-forestillinger, stand-up, moderne og "
     "klassisk drama."),

    ("Den Norske Opera og Ballett - program",
     "https://operaen.no/forestillinger/",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Operaen i Bjoervika - hovedhuset for opera og ballett i Norge. "
     "Aktuelle forestillinger + konserter i Scenen og vinterhagen."),

    # --- Konserter / konserthus -------------------------------------------
    ("Oslo Konserthus - klassiske konserter",
     "https://www.oslokonserthus.no/program/",
     "Frogner", "2026-04-22", "kultur",
     "Oslo Konserthus i Vika - hjemmet for Oslo-Filharmonien. "
     "Klassiske konserter + jazz, verdensmusikk og gjestende artister."),

    ("Sentrum Scene - pop/rock-konserter",
     "https://sentrumscene.no/arrangementer/",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Sentrum Scene paa Arbeidersamfunnets plass - klassiker for "
     "norske og internasjonale band. Program dekker pop, rock, hiphop "
     "og klubb."),

    ("Rockefeller Music Hall",
     "https://www.rockefeller.no/program/",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Rockefeller i Torggata - ikonisk konsertscene siden 1986. "
     "Aktuelle konserter: norske hovedband, internasjonale stjerner "
     "og klubb-arrangementer."),

    ("Oslo Spektrum - store konserter",
     "https://www.oslospektrum.no/arrangementer",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Oslo Spektrum ved Jernbanetorget - Norges stoerste innendoers-"
     "arena. Verdensstjerner, store show og idretts-arrangementer. "
     "Sjekk siden for vaar/sommer-kalender."),

    ("Kulturkirken Jakob - intime konserter",
     "https://jakobkulturkirke.no/program",
     "Gr\u00fcnerl\u00f8kka", "2026-04-22", "kultur",
     "Kulturkirken Jakob paa Torshovgate - tidligere Jakob kirke, "
     "n\u00e5 intimscene for jazz, folk, viser og kammermusikk med "
     "spesiell akustikk."),

    # --- O-loep / orientering ---------------------------------------------
    ("Orientering: Oslo Cup 1 - Sognsvann",
     "https://www.nydalensil.no/orientering/",
     "Nordre Aker", "2026-04-29", "idrett",
     "Oslo Cup er en aarlig serie med korte naerloep (5-8 km) "
     "arrangert av Oslo-klubbene i rotasjon. Vaarens aapningsloep "
     "med utgangspunkt Sognsvann. Aapne klasser for alle nivaaer. "
     "Arrangoer: Nydalens SK. Paamelding via Eventor."),

    ("Orientering: Lillomarka OL naerloep - Linderudkollen",
     "https://www.lillomarkaol.no/",
     "Grorud", "2026-05-06", "idrett",
     "Naerloep i Lillomarka med utgangspunkt Linderudkollen skisenter. "
     "Korte loeyper (C/D) for familier og nybegynnere samt lange "
     "A-loeyper for konkurranseloepere. Arrangeres jevnlig hele "
     "vaar-/sommer-sesongen."),

    ("Orientering: Heming naerloep - Holmenkollen",
     "https://www.heming.no/orientering/",
     "Vestre Aker", "2026-05-13", "idrett",
     "Naerloep arrangert av Heming orientering med start ved "
     "Holmenkollen/Tryvann. Teknisk Nordmarka-terreng med myr, stein "
     "og stier. Paamelding via Eventor; gratis for Heming-medlemmer."),

    ("Orientering: Pinseloepet 2026",
     "https://eventor.orientering.no/Events",
     "Vestre Aker", "2026-05-24", "idrett",
     "Tradisjonsrikt pinseloep med base Frognerseteren. "
     "Langdistanse og mellomdistanse paa pinseloerdag og -soendag. "
     "Trekker orienterings-loepere fra hele Norden."),

    ("Orientering: KM sprint Akershus og Oslo",
     "https://eventor.orientering.no/Events",
     "Frogner", "2026-06-06", "idrett",
     "Kretsmesterskap i sprint-orientering for Akershus og Oslo "
     "Orienteringskrets. Hurtige sprint-traser i Frognerparken og "
     "omliggende bygater. Raske veivalg mellom parkveier og bakker."),

    ("Orientering: Oslo Cup 3 - Oestmarksetra",
     "https://www.nydalensil.no/orientering/",
     "\u00d8stensj\u00f8", "2026-06-17", "idrett",
     "Midtsommer-loep i Oslo Cup-serien. Utgangspunkt Oestmarksetra, "
     "teknisk terreng med mye stein og myr. A-loeype opp mot 12 km, "
     "D-loeype 3 km med enkle poster for barn og nybegynnere."),

    ("Orientering: Koll naerloep - Skullerud",
     "https://koll.no/",
     "Nordstrand", "2026-06-24", "idrett",
     "Naerloep arrangert av IL Koll med start ved Skullerud. "
     "Oestmarka-terreng med variert skog og kupert landskap. Korte og "
     "lange loeyper; gratis proeveloepning for ikke-medlemmer."),

    ("Orientering: Oslo 3-dagers 2026",
     "https://eventor.orientering.no/Events",
     "Vestre Aker", "2026-08-14", "idrett",
     "Tredagers etappefest i Nordmarka med base Frognerseteren. "
     "Ulikt terreng og distanse hver dag; sammenlagtpremier etter "
     "3 etapper. Aapne klasser for alle aldre fra 10 til 85+."),

    ("Orientering: OSI Blindern-sprint",
     "https://osi-o.no/",
     "Nordre Aker", "2026-08-29", "idrett",
     "Sprintloep paa Universitetet i Oslo / Blindern-campus og "
     "omliggende gater. Teknisk sprint-orientering med raske veivalg "
     "mellom bygninger. Arrangoer: Oslo Studenters IL. Aapen "
     "deltakelse."),

    ("Orientering: Oslo-mesterskapet langdistanse",
     "https://eventor.orientering.no/Events",
     "Nordre Aker", "2026-09-05", "idrett",
     "OM individuelt paa lang distanse. Terreng i Nordmarka, ofte "
     "utgangspunkt Ullevaalseter eller Kobberhaug. Klasser H/D 10-85 "
     "samt aapne klasser. Arrangoer roterer blant Oslo-klubbene."),

    ("Orientering: OM stafett 2026",
     "https://eventor.orientering.no/Events",
     "\u00d8stensj\u00f8", "2026-09-12", "idrett",
     "Oslo-mesterskapet stafett med lag fra alle Oslo-klubbene. "
     "3-etappers stafett med vaktskifte paa Skullerud. Profesjonelle "
     "lag og aapne mosjonsklasser samme dag."),

    ("Orientering: Fossum IF naerloep - Vestmarka",
     "https://www.fossumif.no/",
     "Ullern", "2026-09-19", "idrett",
     "Naerloep i Vestmarka/Baerumsmarka arrangert av Fossum IF. "
     "Utgangspunkt Oesternvann. Variert skog med god laebarhet. "
     "Del av ukentlig naerloep-serie mai-september."),

    ("Orientering: Blodslitet 2026",
     "https://eventor.orientering.no/Events",
     "Nordre Aker", "2026-10-10", "idrett",
     "Klassisk langdistanse-loep i Nordmarka. 15-20 km for A-loeypen. "
     "Krevende terreng med myrdrag og sti-kaos. Tradisjonsrikt hoest-"
     "loep som trekker loepere fra hele Oestlandet."),

    ("Orientering: Nattuglen - nattloep i Nordmarka",
     "https://eventor.orientering.no/Events",
     "Vestre Aker", "2026-11-07", "idrett",
     "Nattloep i Nordmarka med hodelykt. Ca. 5-8 km teknisk terreng "
     "i moerket. Del av Nattuglen-karusellen november-februar; "
     "arrangeres i rotasjon av Oslo-klubbene."),

    ("Orientering: O-troll-loepet (for barn)",
     "https://eventor.orientering.no/Events",
     "Vestre Aker", "2026-05-02", "idrett",
     "Barne- og nybegynner-loep med korte, merkede loeyper. Laerings-"
     "poster med moro-oppgaver og enkel navigasjon. Ingen tidmaaling "
     "- ferdigheter og mestring er hovedfokus."),

    # --- Deichman / Oslo bibliotek ----------------------------------------
    ("Sommerles 2026: lesekampanje for barn",
     "https://www.sommerles.no/",
     "Gamle Oslo", "2026-06-01", "kultur",
     "Nasjonal lesekampanje for 1.-7. trinn som starter 1. juni. Deichman "
     "deler ut premier for boeker lest gjennom sommeren. Alle Oslo-filialer "
     "deltar."),

    ("Deichman Bjoervika: Barneloerdag",
     "https://www.deichman.no/bjorvika",
     "Gamle Oslo", "2026-05-09", "kultur",
     "Loerdagsprogram med eventyr, sang og verksted for barn 3-9 aar. Fast "
     "tilbud foerste loerdag hver maaned i hovedbiblioteket."),

    ("Deichman Gr\u00fcnerl\u00f8kka: Forfatterkveld",
     "https://www.deichman.no/grunerlokka",
     "Gr\u00fcnerl\u00f8kka", "2026-05-15", "kultur",
     "Forfatterbesoek og samtale over en halv time, deretter kaffe og "
     "mingling. Foelg Deichman-programmet for hvem som kommer neste gang."),

    ("Deichman T\u00f8yen: Spraakkafe",
     "https://www.deichman.no/toyen",
     "Gamle Oslo", "2026-05-06", "kultur",
     "Uformell spraakkafe for norsk-laerere og internasjonale Oslo-borgere. "
     "Onsdag ettermiddag, alle nivaa velkommen."),

    ("Deichman Majorstuen: Bokstrikk",
     "https://www.deichman.no/majorstuen",
     "Frogner", "2026-05-14", "kultur",
     "Strikkegruppe som moetes over kaffe og en bok. Fast torsdagstilbud. "
     "Gratis, ta med eget prosjekt."),

    ("Deichman Torshov: Lokalhistorielauget",
     "https://www.deichman.no/torshov",
     "Sagene", "2026-05-21", "kultur",
     "Maanedlig foredragskveld om lokalhistorie i Sagene og Torshov. "
     "Samarbeid med Oslo byarkiv og lokale eldre-informanter."),

    ("Deichman Lambertseter: Familiesoendag",
     "https://www.deichman.no/lambertseter",
     "Nordstrand", "2026-05-03", "kultur",
     "Soendags-familieverksted med hoeytlesing, tegning og bokprat. "
     "Passer best 4-10 aar, men hele familien velkommen."),

    ("Deichman Furuset: Flerkulturell leseklubb",
     "https://www.deichman.no/furuset",
     "Alna", "2026-05-20", "kultur",
     "Leseklubb som diskuterer boeker paa flere spraak. Urdu, somali, "
     "arabisk og norsk representert. Annenhver uke."),

    ("Nordisk bibliotekuke 2026",
     "https://www.deichman.no/",
     "Gamle Oslo", "2026-11-09", "kultur",
     "Felles nordisk leseuke der bibliotek i Oslo holder hoeytlesing "
     "paa morgenen og skumring. Samtlige Deichman-filialer deltar."),

    ("Bokstart Oslo: bokpakker til 1-aaringer",
     "https://www.deichman.no/bokstart",
     "Gamle Oslo", "2026-09-15", "kultur",
     "Gratis bokpakke til alle 1-aaringer i Oslo. Leveres via helsestasjon "
     "eller hentes paa Deichman-filialer i loepet av hoesten."),

    # --- Oslo kommune signatur-arrangementer ------------------------------
    ("17. mai: Barnetoget paa Karl Johan",
     "https://www.oslo.kommune.no/17-mai",
     "St. Hanshaugen", "2026-05-17", "arrangement",
     "Det tradisjonelle barnetoget der alle Oslos skoler deltar. Starter "
     "kl 10 fra Akershus festning og gaar opp Karl Johan til Slottet. "
     "Hilsen fra kongefamilien paa balkongen."),

    ("17. mai: Russeparaden gjennom sentrum",
     "https://www.oslo.kommune.no/17-mai",
     "St. Hanshaugen", "2026-05-17", "arrangement",
     "Russen gaar gjennom sentrum etter barnetoget. Samling paa Egertorvet, "
     "felles parade ned Karl Johan og avslutning paa Raadhusplassen."),

    ("Ungdommens Kulturmoenstring Oslo 2026",
     "https://ukm.no/oslo",
     "Gr\u00fcnerl\u00f8kka", "2026-03-14", "kultur",
     "Fylkesmoenstringen for Oslo med unge artister fra hele byen. Dans, "
     "musikk, visuell kunst og film. Vinnerne gaar videre til UKM-festivalen "
     "i Trondheim."),

    ("Oslo Mangfoldsfestival 2026",
     "https://www.oslo.kommune.no/mangfold",
     "Gamle Oslo", "2026-06-06", "arrangement",
     "Aarlig festival som feirer kulturell og spraaklig mangfold i Oslo. "
     "Matboder, musikk og dans fra over 40 kulturer i T\u00f8yenparken."),

    ("Sankthansbaal ved Frognerkilen",
     "https://www.oslo.kommune.no/sankthans",
     "Frogner", "2026-06-23", "arrangement",
     "Offisielt kommune-baal paa Frognerkilen, arrangert av Bymiljoeetaten. "
     "Familiearrangement fra kl 19 med poelsegrilling og friluftsmusikk."),

    ("Frivillighetsdagen 2026",
     "https://www.oslo.kommune.no/frivillighet",
     "St. Hanshaugen", "2026-12-05", "arrangement",
     "Oslo kommune hedrer byens frivillige. Priser, seremoni paa Raadhuset "
     "og stands paa Raadhusplassen for over 200 frivillige organisasjoner."),

    ("Julegrantenning paa Stortorvet",
     "https://www.oslo.kommune.no/jul",
     "Gamle Oslo", "2026-11-28", "arrangement",
     "Den offisielle julegrantenningen i Oslo sentrum. Ordfoerer holder "
     "tale, barnekor synger og grana tennes kl 17. Start paa julesesongen."),

    ("Filmhuset hoestprogram 2026",
     "https://www.filmhuset.no/",
     "St. Hanshaugen", "2026-09-01", "kultur",
     "Cinemateket i Filmhuset aapner hoestsesongen med retrospektiv og "
     "internasjonale klassikere. Maanedlige tema-programmer."),

    ("Operaens lunsjkonserter 2026 vaar",
     "https://operaen.no/lunsjkonserter",
     "Gamle Oslo", "2026-05-08", "kultur",
     "Gratis 30-min lunsjkonserter i foajeen fredag kl 12. Operaens "
     "musikere og ensembler. Mest klassisk, av og til crossover."),

    ("Byarkivets aapne dag 2026",
     "https://www.oslo.kommune.no/byarkivet",
     "St. Hanshaugen", "2026-10-17", "arrangement",
     "Byarkivet viser fram kildene: gamle bygningstegninger, skoleprotokoller "
     "og familiedokumenter. Slektsforskere og lokalhistorikere til stede."),

    ("Nasjonalmuseets sommerutstilling 2026",
     "https://www.nasjonalmuseet.no/",
     "Frogner", "2026-06-12", "kultur",
     "Storformat-utstilling paa nybygget. Tema og kurator offentliggjoeres "
     "paa vaarparten. Barnefamilieaktiviteter hele sommeren."),

    ("Munchmuseet: Sommersesong 2026",
     "https://www.munchmuseet.no/",
     "Gamle Oslo", "2026-06-01", "kultur",
     "Sommersesongens hovedutstilling aapnes i Munchmuseet paa Bjoervika. "
     "Lengre aapningstider og ekstra guidede turer gjennom sommeren."),

    ("Oslo Internasjonale Filmfestival 2026",
     "https://oslofilmfestival.com/",
     "St. Hanshaugen", "2026-10-28", "kultur",
     "Oslos eldste filmfestival. Over 150 filmer paa Vega, Saga, Gimle og "
     "andre sentrumskinoer. Fra dokumentar til kunstfilm."),
    # --- Markastuer ---------------------------------------------------------
    ("Skjennungstua aapner sommersesongen",
     "https://skjennungstua.no/",
     "Nordre Aker", "2026-05-02", "arrangement",
     "Skjennungstua, Skiforeningens serveringsstue i Nordmarka nord for "
     "Sognsvann, aapner loerdags- og soendags-kafeen for sommeren. Vaffelduft "
     "og utsikt mot Skjennungen. Turstart fra Frognerseteren eller Sognsvann."),

    ("Kikutstua / Kikut (DNT-hytte)",
     "https://kikut.dntoslo.no/",
     "Nordre Aker", "2026-05-16", "arrangement",
     "DNT Oslo og Omegn sin hytte ved Kikut i Nordmarka. Overnatting, kafe "
     "og betjent servering paa helger. Populaer stoppestasjon paa lange "
     "skiturer og sykkelturer gjennom Nordmarka."),

    ("Mariholtet serveringsstue aapner",
     "https://mariholtet.no/",
     "Alna", "2026-04-25", "arrangement",
     "Mariholtet i Oestmarka aapner vaffelkafeen for vaar- og sommersesongen. "
     "Populaer endestasjon paa turer fra Haugerud, Oppsal og Sarabraaten. "
     "Bamsen Brumm-tradisjon og skogsvandring."),

    ("Lilloseter serveringsstue",
     "https://lilloseter.no/",
     "Nordre Aker", "2026-05-02", "arrangement",
     "Lilloseter i Nordmarka — betjent stue med vafler og kaffe. "
     "Kort avstand fra Lillomarka skistadion og Solemskogen. "
     "Turstart fra Movann eller Linderudkollen."),

    ("Sinober kafe og overnatting",
     "https://sinober.no/",
     "Alna", "2026-05-16", "arrangement",
     "Sinober i Oestmarka — kafe og liten overnatting helgene. "
     "Kort gaatur fra Nokleholtet. Betjent sesong fra mai."),

    ("Rustadsaga sportsstue",
     "https://rustadsaga.no/",
     "\u00d8stensj\u00f8", "2026-04-25", "arrangement",
     "Rustadsaga ved Noeklevann — serveringsstue og badeplass. "
     "Populaer utgangsport for tur, jogging og bading i Oestmarka. "
     "Kafeen er aapen hele sommeren."),

    ("Sandbakken sportsstue",
     "https://sandbakken-oestmarka.no/",
     "Nordstrand", "2026-04-25", "arrangement",
     "Sandbakken i Oestmarka — sportsstue og servering. "
     "Klassisk tur-maal fra Skullerud. Paasketradisjon og sommer-kafe. "
     "Grillplass og teltomraade like ved."),

    ("Kobberhaughytta",
     "https://kobberhaug.dntoslo.no/",
     "Nordre Aker", "2026-06-01", "arrangement",
     "DNT Oslo og Omegn sin betjente hytte i Nordmarka. Overnatting, "
     "middag og frokost. Kort avstand fra Blaataarn og Kikutstua."),

]


def load_events() -> list[dict]:
    """Returner eventene som normaliserte story-dicts."""
    now_iso = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    for title, url, bydel, date_iso, category, summary in EVENTS:
        out.append({
            "id": _event_id(url, title),
            "bydel": bydel,
            "title": title,
            "url": url,
            "source": "Bydelsnytt kuratert",
            "source_id": "events",
            "published_iso": f"{date_iso}T00:00:00+00:00",
            "date_iso": date_iso,
            "summary": summary,
            "category": category,
            "fetched_at_iso": now_iso,
        })
    return out


if __name__ == "__main__":
    events = load_events()
    print(f"Totalt {len(events)} kuratere arrangementer")
    from collections import Counter
    per_cat = Counter(e["category"] for e in events)
    per_bydel = Counter(e["bydel"] for e in events)
    for k, v in per_cat.items():
        print(f"  kategori {k}: {v}")
    print("---")
    for k, v in per_bydel.items():
        print(f"  bydel {k}: {v}")
