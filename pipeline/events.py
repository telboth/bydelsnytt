"""Kuratert seed-liste av Oslo-arrangementer: løp, sykkelritt, skirenn,
fotballkamper, festivaler, kulturarrangementer.

Data kommer fra årlige, tilbakevendende arrangementer. Datoer er beste estimat
basert på typisk helg-mønster (f.eks. Oslo Maraton = 3. lørdag i september).
Sjekk arranger-siden for eksakt dato/tid.

Hver event er et dict som matcher RawStory.to_dict()-formatet. Pipeline-run
merge-er disse på lik linje med RSS/HTML-scrapede saker, og classify-modulen
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
    # --- Løp / mosjonsløp -------------------------------------------------
    ("Sentrumsløpet 2026",
     "https://www.sentrumslopet.no/",
     "Frogner", "2026-04-25", "idrett",
     "Oslos klassiske bygateløpet gjennom sentrum. 10 km med start og mål "
     "på Rådhusplassen. Ett av Norges største byløp, arrangeres årlig "
     "siste lørdag i april."),

    ("Holmenkollstafetten 2026",
     "https://holmenkollstafetten.no/",
     "Frogner", "2026-05-09", "idrett",
     "Årets store stafettlopp med 15 etapper i sentrum. 2. lørdag i mai. "
     "Trekker over 40.000 løpere fra skoler, bedrifter og klubber."),

    ("Styrkeprøven 2026 (Trondheim-Oslo)",
     "https://www.styrkeproven.no/",
     "Frogner", "2026-06-20", "idrett",
     "Nordens største sykkelritt på landevei. 540 km fra Trondheim til "
     "Oslo; mål i Frognerparken. Arrangeres tredje helg i juni."),

    ("Oslo Grand Prix 2026 (sykkel)",
     "https://nb-no.facebook.com/bjerketravbane/",
     "Frogner", "2026-06-13", "idrett",
     "Kriteriumritt i Oslo sentrum. Profesjonelle og mosjonist-ritt samme "
     "dag. Ruten går gjennom Frogner og sentrum."),

    ("Oslo Triathlon 2026",
     "https://oslotri.com/",
     "Nordre Aker", "2026-08-22", "idrett",
     "Byens største triatlon med svømming i Sognsvann, sykkel og løp "
     "rundt Nordmarka/Nordre Aker. Sprint-, olympisk og halv-distanse."),

    ("Norway Cup 2026",
     "https://www.norwaycup.no/",
     "Gamle Oslo", "2026-07-26", "idrett",
     "Verdens største fotballturnering for barn og ungdom på "
     "Ekebergsletta. En ukes spill med over 2000 lag fra hele verden."),

    ("Grefsenkollen opp 2026",
     "https://www.grefsenkollenopp.no/",
     "Nordre Aker", "2026-05-20", "idrett",
     "Motbakkeløp arrangert av Nydalens Skiklub. Fra Muselunden (110 moh) "
     "via Kjelsåsveien og Grefsenkollveien til Grefsenkollen Restaurant "
     "(380 moh). 4,7 km, 6 % stigning, 270 hm. Onsdag 20. mai 2026, "
     "start kl 18:30."),

    ("Oslos bratteste 2026 (tidligere Tryvann opp)",
     "https://oslosbratteste.no/",
     "Vestre Aker", "2026-09-12", "idrett",
     "Motbakkeløp fra Frognerseteren til Tryvannstårnet. Kort men bratt, "
     "ca 3,5 km. Tidligere kjent som Tryvann opp, omdøpt til Oslos bratteste."),

    ("Oslo Maraton 2026",
     "https://www.oslomaraton.no/",
     "Frogner", "2026-09-19", "idrett",
     "Norges største maraton. Maratonløp, halvmaraton, 10 km og barneløp "
     "gjennom sentrum, Frogner, Bjørvika og Grünerløkka. Start/mål på "
     "Rådhusplassen."),

    ("Bygdoymila 2026",
     "https://www.facebook.com/Bygdoymila/",
     "Frogner", "2026-10-18", "idrett",
     "Terrengløp rundt Bygdøy. Klassisk halvmaraton på stier gjennom "
     "kongsgården og Bygdøy-skogen. Årlig i oktober."),

    # --- Kultur / festivaler ------------------------------------------------
    ("17. mai-feiringen 2026",
     "https://www.oslo.kommune.no/17-mai/",
     "Frogner", "2026-05-17", "kultur",
     "Barnetoget går opp Karl Johan forbi Slottet der Kongefamilien hilser. "
     "Hovedarrangementer i Slottsparken og langs paraderuten."),

    ("Musikkfest Oslo 2026",
     "https://musikkfest.no/",
     "St. Hanshaugen", "2026-06-20", "kultur",
     "Gratis musikkfestival med over 1000 artister på scenes i hele "
     "sentrum. Arrangeres lørdag nærmest sankthans hver sommer."),

    ("Oslo Pride Parade 2026",
     "https://www.oslopride.no/",
     "Frogner", "2026-06-27", "kultur",
     "Paraden går fra Grønland til Rådhusplassen. Pride Park arrangeres "
     "samme uke i Spikersuppa og Kontraskjæret."),

    ("Øyafestivalen 2026",
     "https://www.oyafestivalen.no/",
     "Gamle Oslo", "2026-08-04", "kultur",
     "Norges største urbane musikkfestival i Tøyenparken. Fire dager med "
     "nasjonale og internasjonale hovedartister. Klimanøytral og "
     "økologisk profilert."),

    ("Oslo Jazzfestival 2026",
     "https://www.oslojazz.no/",
     "St. Hanshaugen", "2026-08-17", "kultur",
     "En uke med jazz på scener rundt Oslo sentrum: Nasjonal jazzscene, "
     "Rockefeller, Kulturkirken Jakob og flere utearenaer."),

    ("Kulturnatt Oslo 2026",
     "https://www.kulturnatt.no/",
     "St. Hanshaugen", "2026-09-11", "kultur",
     "En kveld der over 150 kulturinstitusjoner holder åpent gratis. "
     "Museer, teatre, gallerier og bibliotek i hele sentrum."),

    ("Inferno Metal Festival 2026",
     "https://infernofestival.net/",
     "St. Hanshaugen", "2026-04-29", "kultur",
     "Internasjonal metalfestival over 4 dager på Rockefeller og John "
     "Dee. Påskehelt med norske og internasjonale hovedartister."),

    # --- Skirenn (vinter 2027) ----------------------------------------------
    ("Holmenkollmarsjen 2027",
     "https://www.holmenkollmarsjen.no/",
     "Vestre Aker", "2027-03-06", "idrett",
     "Turrenn på 42 km eller 21 km i Nordmarka. Start og mål ved "
     "Holmenkollen skistadion. Forste lørdag i mars."),

    ("FIS World Cup Holmenkollen 2027",
     "https://www.skiforeningen.no/holmenkollen/holmenkollen-skifestival/",
     "Vestre Aker", "2027-03-13", "idrett",
     "Verdenscup-helg i langrenn, hopp og kombinert på Holmenkollen. "
     "Over 100.000 tilskuere over tre dager."),

    ("Sognsvann rundt medsols 2027",
     "https://kondis.no/",
     "Nordre Aker", "2027-02-07", "idrett",
     "Turrenn rundt Sognsvann og inn i Nordmarka. Tre distanser: 5 km, "
     "10 km og 20 km. Klassisk familie-skirenn."),


    # --- Loppemarkeder (vårloppis 2026) -----------------------------------
    ("Ris skoles loppemarked 2026",
     "https://ris.osloskolen.no/",
     "Vestre Aker", "2026-05-02", "arrangement",
     "Årlig vårloppis arrangert av FAU på Ris skole. Inntekter går til "
     "elevaktiviteter. Innlevering fredag, salg lørdag. Klassiker på "
     "vestkanten."),

    ("Nordberg skoles loppemarked 2026",
     "https://nordberg.osloskolen.no/",
     "Nordre Aker", "2026-05-09", "arrangement",
     "FAU-loppis på Nordberg skole med klær, bøker, sportsutstyr og "
     "kjøkkenting. Salg lørdag 10-14 i gymsalen."),

    ("T\u00e5sen skoles loppemarked 2026",
     "https://tasen.osloskolen.no/",
     "Nordre Aker", "2026-04-25", "arrangement",
     "Tradisjonsrik vårloppis på T\u00e5sen skole. FAU dekker overskudd "
     "til skoleturer. Innlevering torsdag, salg lørdag 10-13."),

    ("Vahl skoles loppemarked 2026",
     "https://vahl.osloskolen.no/",
     "Gamle Oslo", "2026-05-16", "arrangement",
     "Vårloppis på Vahl skole på Gr\u00f8nland. Mangfoldig loppis med "
     "fokus på bærekraftig gjenbruk i lokalmiljøet."),

    ("Ellingsrudåsen skoles h\u00f8stloppis 2026",
     "https://ellingsrudasen.osloskolen.no/",
     "Alna", "2026-09-26", "arrangement",
     "H\u00f8st-loppemarked i Furuset-området. Innsamling i forkant, stort "
     "utvalg av ting til hjem og fritid."),

    # --- Speidergrupper (lokale aktiviteter) -------------------------------
    ("Ris speidergruppe - ukentlige m\u00f8ter",
     "https://speiding.no/oslokrets",
     "Vestre Aker", "2026-04-22", "arrangement",
     "Ris speidergruppe har ukentlige m\u00f8ter for bevere, småspeidere, "
     "speidere og rovere. M\u00f8tested: Speiderhuset ved Ris stasjon. "
     "Aktiviteter: friluftsliv, patruljearbeid, hiking i Nordmarka."),

    ("Nordstrand speidergruppe - aktiviteter v\u00e5r 2026",
     "https://speiding.no/oslokrets",
     "Nordstrand", "2026-04-24", "arrangement",
     "Nordstrand speidergruppe - en av Oslos største. Ukentlige m\u00f8ter "
     "på Tallberget. V\u00e5rens høydepunkt: patruljetur i Østmarka "
     "og pinseleir for alle aldersgrupper."),

    ("Sagene speidergruppe - aktiviteter",
     "https://speiding.no/oslokrets",
     "Sagene", "2026-04-23", "arrangement",
     "Sagene speidergruppe samler speidere fra Sagene, Torshov og "
     "Bjølsen. M\u00f8ter ved Bjørkelunden. Fokus på byspeiding og "
     "tur til Oslomarka."),

    ("Grorud speidergruppe",
     "https://speiding.no/oslokrets",
     "Grorud", "2026-04-25", "arrangement",
     "Grorud speidergruppe m\u00f8tes ukentlig ved Grorud kirke. "
     "Aktiviteter spenner fra friluftsliv i Lillomarka til sosiale "
     "prosjekter i bydelen."),

    ("Holmlia speidergruppe",
     "https://speiding.no/oslokrets",
     "S\u00f8ndre Nordstrand", "2026-04-22", "arrangement",
     "Holmlia speidergruppe - aktiv gruppe i et flerkulturelt nabolag. "
     "M\u00f8ter i Holmlia-området med fokus på integrering og "
     "friluftsliv i Østmarka."),

    ("Gr\u00fcnerl\u00f8kka speidergruppe",
     "https://speiding.no/oslokrets",
     "Gr\u00fcnerl\u00f8kka", "2026-04-28", "arrangement",
     "Gr\u00fcnerl\u00f8kka speidergruppe - byspeidere på østkanten. "
     "M\u00f8ter på Sofienberg. Kombinerer urbane aktiviteter med "
     "turer til Marka."),

    # --- Lions-klubber i Oslo ---------------------------------------------
    ("Lions Club Oslo Nordstrand - aktiviteter",
     "https://www.lions.no/oslonordstrand/",
     "Nordstrand", "2026-05-05", "arrangement",
     "Lions Club Oslo Nordstrand støtter lokalt ungdomsarbeid og "
     "humanitære prosjekter. Månedlige m\u00f8ter + årlig juleaksjon "
     "og innsamling til Lions Tulipan."),

    ("Lions Club Oslo/Vestre Aker",
     "https://www.lions.no/oslovestreaker/",
     "Vestre Aker", "2026-05-12", "arrangement",
     "Lions Club Oslo/Vestre Aker - aktive siden 1965. Arrangerer "
     "julemarked, tulipan-aksjon og støtter eldrearbeid i bydelen."),

    ("Lions Club Oslo/Groruddalen",
     "https://www.lions.no/oslogroruddalen/",
     "Grorud", "2026-05-19", "arrangement",
     "Lions Club Oslo/Groruddalen drifter årlig loppemarked og "
     "tulipan-aksjon. Midler går til ungdomsaktiviteter og "
     "humanitært arbeid lokalt i Groruddalen."),

    ("Lions Club Oslo/Gamle Oslo",
     "https://www.lions.no/oslogamleoslo/",
     "Gamle Oslo", "2026-05-26", "arrangement",
     "Lions Club Oslo/Gamle Oslo støtter mangfoldige lokale "
     "prosjekter på Tøyen og Gr\u00f8nland. Aktive i Tulipanaksjonen "
     "hver vår og i julehjelp hver desember."),

    # --- Kinopremierer / kinosaler ----------------------------------------
    ("Vega Scene - aktuelle filmer",
     "https://vegascene.no/",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Vega Scene på Hausmannsplass viser arthouse-film, kortfilm og "
     "dokumentarer. Kinotek-profil med norske og internasjonale "
     "premierer, Q&A og filmklubber."),

    ("Saga Kino - storfilmer våren 2026",
     "https://www.cinemateket.no/kino/saga/",
     "Frogner", "2026-04-22", "kultur",
     "Saga Kino ved Klingenberg viser storfilmer på stor leredet. "
     "Aktuell vårsesong med norske og amerikanske premierer."),

    ("Colosseum Kino - IMAX og premierer",
     "https://www.cinemateket.no/kino/colosseum/",
     "Frogner", "2026-04-22", "kultur",
     "Colosseum på Majorstua - Nordens største kinosal. Storfilm-"
     "premierer, IMAX-visninger og spesialarrangementer. Klassisk "
     "kinopalass bygd i 1928."),

    ("Gimle Kino - arthouse og repertoire",
     "https://www.cinemateket.no/kino/gimle/",
     "Frogner", "2026-04-22", "kultur",
     "Gimle Kino på Bygdøy all\u00e9 viser kuraterte filmer og "
     "klassikere i koselige lokaler. Premiere for utvalgte norske og "
     "europeiske filmer."),

    # --- Teater-forestillinger --------------------------------------------
    ("Nationaltheatret - aktuelt program",
     "https://www.nationaltheatret.no/forestillinger",
     "Frogner", "2026-04-22", "kultur",
     "Nationaltheatret spiller klassikere og samtidsdrama på "
     "Hovedscenen og Amfiscenen. Oslos hovedteater med norsk og "
     "internasjonal dramatikk."),

    ("Det Norske Teatret - nynorsk scene",
     "https://www.detnorsketeatret.no/",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Det Norske Teatret på Kristian IV's gate - Norges nynorsk-"
     "scene. Spiller egne produksjoner og gjestende ensembler. "
     "Inkluderende program for unge."),

    ("Oslo Nye Teater",
     "https://www.oslonye.no/forestillinger",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Oslo Nye Teater på Centralteatret + Hovedscenen. Bredt "
     "repertoar med familie-forestillinger, stand-up, moderne og "
     "klassisk drama."),

    ("Den Norske Opera og Ballett - program",
     "https://operaen.no/forestillinger/",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Operaen i Bjørvika - hovedhuset for opera og ballett i Norge. "
     "Aktuelle forestillinger + konserter i Scenen og vinterhagen."),

    # --- Konserter / konserthus -------------------------------------------
    ("Oslo Konserthus - klassiske konserter",
     "https://www.oslokonserthus.no/program/",
     "Frogner", "2026-04-22", "kultur",
     "Oslo Konserthus i Vika - hjemmet for Oslo-Filharmonien. "
     "Klassiske konserter + jazz, verdensmusikk og gjestende artister."),

    ("Sentrum Scene - pop/rock-konserter",
     "https://www.sentrumscene.no/",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Sentrum Scene på Arbeidersamfunnets plass - klassiker for "
     "norske og internasjonale band. Program dekker pop, rock, hiphop "
     "og klubb."),

    ("Rockefeller Music Hall",
     "https://www.rockefeller.no/",
     "St. Hanshaugen", "2026-04-22", "kultur",
     "Rockefeller i Torggata - ikonisk konsertscene siden 1986. "
     "Aktuelle konserter: norske hovedband, internasjonale stjerner "
     "og klubb-arrangementer."),

    ("Oslo Spektrum - store konserter",
     "https://www.oslospektrum.no/arrangementer",
     "Gamle Oslo", "2026-04-22", "kultur",
     "Oslo Spektrum ved Jernbanetorget - Norges største innendørs-"
     "arena. Verdensstjerner, store show og idretts-arrangementer. "
     "Sjekk siden for vår/sommer-kalender."),

    ("Kulturkirken Jakob - intime konserter",
     "https://kulturkirken.no/program",
     "Gr\u00fcnerl\u00f8kka", "2026-04-22", "kultur",
     "Kulturkirken Jakob på Torshovgate - tidligere Jakob kirke, "
     "n\u00e5 intimscene for jazz, folk, viser og kammermusikk med "
     "spesiell akustikk."),

    # --- O-løp / orientering ---------------------------------------------
    ("Orientering: Oslo Cup 1 - Sognsvann",
     "https://orientering.no/",
     "Nordre Aker", "2026-04-29", "idrett",
     "Oslo Cup er en årlig serie med korte nærløp (5-8 km) "
     "arrangert av Oslo-klubbene i rotasjon. Vårens åpningsløp "
     "med utgangspunkt Sognsvann. Åpne klasser for alle nivåer. "
     "Arrangør: Nydalens SK. Påmelding via Eventor."),

    ("Orientering: Lillomarka OL nærløp - Linderudkollen",
     "https://no.wikipedia.org/wiki/Lillomarka_Orienteringslag",
     "Grorud", "2026-05-06", "idrett",
     "Nærløp i Lillomarka med utgangspunkt Linderudkollen skisenter. "
     "Korte løyper (C/D) for familier og nybegynnere samt lange "
     "A-løyper for konkurranseløpere. Arrangeres jevnlig hele "
     "vår-/sommer-sesongen."),

    ("Orientering: Heming nærløp - Holmenkollen",
     "https://www.heming.no/orientering/",
     "Vestre Aker", "2026-05-13", "idrett",
     "Nærløp arrangert av Heming orientering med start ved "
     "Holmenkollen/Tryvann. Teknisk Nordmarka-terreng med myr, stein "
     "og stier. Påmelding via Eventor; gratis for Heming-medlemmer."),

    ("Orientering: Pinseløpet 2026",
     "https://orientering.no/",
     "Vestre Aker", "2026-05-24", "idrett",
     "Tradisjonsrikt pinseløp med base Frognerseteren. "
     "Langdistanse og mellomdistanse på pinselørdag og -søndag. "
     "Trekker orienterings-løpere fra hele Norden."),

    ("Orientering: KM sprint Akershus og Oslo",
     "https://orientering.no/",
     "Frogner", "2026-06-06", "idrett",
     "Kretsmesterskap i sprint-orientering for Akershus og Oslo "
     "Orienteringskrets. Hurtige sprint-traser i Frognerparken og "
     "omliggende bygater. Raske veivalg mellom parkveier og bakker."),

    ("Orientering: Oslo Cup 3 - Østmarksetra",
     "https://orientering.no/",
     "\u00d8stensj\u00f8", "2026-06-17", "idrett",
     "Midtsommer-løp i Oslo Cup-serien. Utgangspunkt Østmarksetra, "
     "teknisk terreng med mye stein og myr. A-løype opp mot 12 km, "
     "D-løype 3 km med enkle poster for barn og nybegynnere."),

    ("Orientering: Koll nærløp - Skullerud",
     "https://koll.no/",
     "Nordstrand", "2026-06-24", "idrett",
     "Nærløp arrangert av IL Koll med start ved Skullerud. "
     "Østmarka-terreng med variert skog og kupert landskap. Korte og "
     "lange løyper; gratis prøveløpning for ikke-medlemmer."),

    ("Orientering: Oslo 3-dagers 2026",
     "https://orientering.no/",
     "Vestre Aker", "2026-08-14", "idrett",
     "Tredagers etappefest i Nordmarka med base Frognerseteren. "
     "Ulikt terreng og distanse hver dag; sammenlagtpremier etter "
     "3 etapper. Åpne klasser for alle aldre fra 10 til 85+."),

    ("Orientering: OSI Blindern-sprint",
     "https://orientering.no/",
     "Nordre Aker", "2026-08-29", "idrett",
     "Sprintløp på Universitetet i Oslo / Blindern-campus og "
     "omliggende gater. Teknisk sprint-orientering med raske veivalg "
     "mellom bygninger. Arrangør: Oslo Studenters IL. Åpen "
     "deltakelse."),

    ("Orientering: Oslo-mesterskapet langdistanse",
     "https://orientering.no/",
     "Nordre Aker", "2026-09-05", "idrett",
     "OM individuelt på lang distanse. Terreng i Nordmarka, ofte "
     "utgangspunkt Ullevålseter eller Kobberhaug. Klasser H/D 10-85 "
     "samt åpne klasser. Arrangør roterer blant Oslo-klubbene."),

    ("Orientering: OM stafett 2026",
     "https://orientering.no/",
     "\u00d8stensj\u00f8", "2026-09-12", "idrett",
     "Oslo-mesterskapet stafett med lag fra alle Oslo-klubbene. "
     "3-etappers stafett med vaktskifte på Skullerud. Profesjonelle "
     "lag og åpne mosjonsklasser samme dag."),

    ("Orientering: Fossum IF nærløp - Vestmarka",
     "https://www.fossumif.no/",
     "Ullern", "2026-09-19", "idrett",
     "Nærløp i Vestmarka/Bærumsmarka arrangert av Fossum IF. "
     "Utgangspunkt Østernvann. Variert skog med god lesbarhet. "
     "Del av ukentlig nærløp-serie mai-september."),

    ("Orientering: Blodslitet 2026",
     "https://orientering.no/",
     "Nordre Aker", "2026-10-10", "idrett",
     "Klassisk langdistanse-løp i Nordmarka. 15-20 km for A-løypen. "
     "Krevende terreng med myrdrag og sti-kaos. Tradisjonsrikt høst-"
     "løp som trekker løpere fra hele Østlandet."),

    ("Orientering: Nattuglen - nattløp i Nordmarka",
     "https://orientering.no/",
     "Vestre Aker", "2026-11-07", "idrett",
     "Nattløp i Nordmarka med hodelykt. Ca. 5-8 km teknisk terreng "
     "i mørket. Del av Nattuglen-karusellen november-februar; "
     "arrangeres i rotasjon av Oslo-klubbene."),

    ("Orientering: O-troll-løpet (for barn)",
     "https://orientering.no/",
     "Vestre Aker", "2026-05-02", "idrett",
     "Barne- og nybegynner-løp med korte, merkede løyper. Lærings-"
     "poster med moro-oppgaver og enkel navigasjon. Ingen tidmåling "
     "- ferdigheter og mestring er hovedfokus."),

    # --- Deichman / Oslo bibliotek ----------------------------------------
    ("Sommerles 2026: lesekampanje for barn",
     "https://www.sommerles.no/",
     "Gamle Oslo", "2026-06-01", "kultur",
     "Nasjonal lesekampanje for 1.-7. trinn som starter 1. juni. Deichman "
     "deler ut premier for bøker lest gjennom sommeren. Alle Oslo-filialer "
     "deltar."),

    ("Deichman Bjørvika: Barnelørdag",
     "https://deichman.no/aktuelt",
     "Gamle Oslo", "2026-05-09", "kultur",
     "Lørdagsprogram med eventyr, sang og verksted for barn 3-9 år. Fast "
     "tilbud første lørdag hver måned i hovedbiblioteket."),

    ("Deichman Gr\u00fcnerl\u00f8kka: Forfatterkveld",
     "https://deichman.no/aktuelt",
     "Gr\u00fcnerl\u00f8kka", "2026-05-15", "kultur",
     "Forfatterbesøk og samtale over en halv time, deretter kaffe og "
     "mingling. Følg Deichman-programmet for hvem som kommer neste gang."),

    ("Deichman T\u00f8yen: Språkkafé",
     "https://deichman.no/aktuelt",
     "Gamle Oslo", "2026-05-06", "kultur",
     "Uformell språkkafe for norsk-laerere og internasjonale Oslo-borgere. "
     "Onsdag ettermiddag, alle nivå velkommen."),

    ("Deichman Majorstuen: Bokstrikk",
     "https://www.deichman.no/majorstuen",
     "Frogner", "2026-05-14", "kultur",
     "Strikkegruppe som møtes over kaffe og en bok. Fast torsdagstilbud. "
     "Gratis, ta med eget prosjekt."),

    ("Deichman Torshov: Lokalhistorielauget",
     "https://www.deichman.no/torshov",
     "Sagene", "2026-05-21", "kultur",
     "Månedlig foredragskveld om lokalhistorie i Sagene og Torshov. "
     "Samarbeid med Oslo byarkiv og lokale eldre-informanter."),

    ("Deichman Lambertseter: Familiesøndag",
     "https://www.deichman.no/lambertseter",
     "Nordstrand", "2026-05-03", "kultur",
     "Søndags-familieverksted med høytlesing, tegning og bokprat. "
     "Passer best 4-10 år, men hele familien velkommen."),

    ("Deichman Furuset: Flerkulturell leseklubb",
     "https://www.deichman.no/furuset",
     "Alna", "2026-05-20", "kultur",
     "Leseklubb som diskuterer bøker på flere språk. Urdu, somali, "
     "arabisk og norsk representert. Annenhver uke."),

    ("Nordisk bibliotekuke 2026",
     "https://www.deichman.no/",
     "Gamle Oslo", "2026-11-09", "kultur",
     "Felles nordisk leseuke der bibliotek i Oslo holder høytlesing "
     "på morgenen og skumring. Samtlige Deichman-filialer deltar."),

    ("Bokstart Oslo: bokpakker til 1-åringer",
     "https://deichman.no/aktuelt",
     "Gamle Oslo", "2026-09-15", "kultur",
     "Gratis bokpakke til alle 1-åringer i Oslo. Leveres via helsestasjon "
     "eller hentes på Deichman-filialer i løpet av høsten."),

    # --- Oslo kommune signatur-arrangementer ------------------------------
    ("17. mai: Barnetoget på Karl Johan",
     "https://www.oslo.kommune.no/17-mai",
     "St. Hanshaugen", "2026-05-17", "arrangement",
     "Det tradisjonelle barnetoget der alle Oslos skoler deltar. Starter "
     "kl 10 fra Akershus festning og går opp Karl Johan til Slottet. "
     "Hilsen fra kongefamilien på balkongen."),

    ("17. mai: Russeparaden gjennom sentrum",
     "https://www.oslo.kommune.no/17-mai",
     "St. Hanshaugen", "2026-05-17", "arrangement",
     "Russen går gjennom sentrum etter barnetoget. Samling på Egertorvet, "
     "felles parade ned Karl Johan og avslutning på Rådhusplassen."),

    ("Ungdommens Kulturmønstring Oslo 2026",
     "https://ukm.no/sted/oslo",
     "Gr\u00fcnerl\u00f8kka", "2026-03-14", "kultur",
     "Fylkesmønstringen for Oslo med unge artister fra hele byen. Dans, "
     "musikk, visuell kunst og film. Vinnerne går videre til UKM-festivalen "
     "i Trondheim."),

    ("Oslo Mangfoldsfestival 2026",
     "https://www.oslo.kommune.no/",
     "Gamle Oslo", "2026-06-06", "arrangement",
     "Årlig festival som feirer kulturell og språklig mangfold i Oslo. "
     "Matboder, musikk og dans fra over 40 kulturer i T\u00f8yenparken."),

    ("Sankthansbål ved Frognerkilen",
     "https://www.oslo.kommune.no/",
     "Frogner", "2026-06-23", "arrangement",
     "Offisielt kommune-bål på Frognerkilen, arrangert av Bymiljøetaten. "
     "Familiearrangement fra kl 19 med pølsegrilling og friluftsmusikk."),

    ("Frivillighetsdagen 2026",
     "https://www.oslo.kommune.no/frivillighet",
     "St. Hanshaugen", "2026-12-05", "arrangement",
     "Oslo kommune hedrer byens frivillige. Priser, seremoni på Rådhuset "
     "og stands på Rådhusplassen for over 200 frivillige organisasjoner."),

    ("Julegrantenning på Stortorvet",
     "https://www.oslo.kommune.no/",
     "Gamle Oslo", "2026-11-28", "arrangement",
     "Den offisielle julegrantenningen i Oslo sentrum. Ordfører holder "
     "tale, barnekor synger og grana tennes kl 17. Start på julesesongen."),

    ("Filmhuset høstprogram 2026",
     "https://www.cinemateket.no/",
     "St. Hanshaugen", "2026-09-01", "kultur",
     "Cinemateket i Filmhuset åpner høstsesongen med retrospektiv og "
     "internasjonale klassikere. Månedlige tema-programmer."),

    ("Operaens lunsjkonserter 2026 vår",
     "https://operaen.no/forestillinger-og-konserter/",
     "Gamle Oslo", "2026-05-08", "kultur",
     "Gratis 30-min lunsjkonserter i foajeen fredag kl 12. Operaens "
     "musikere og ensembler. Mest klassisk, av og til crossover."),

    ("Byarkivets åpne dag 2026",
     "https://www.oslo.kommune.no/byarkivet",
     "St. Hanshaugen", "2026-10-17", "arrangement",
     "Byarkivet viser fram kildene: gamle bygningstegninger, skoleprotokoller "
     "og familiedokumenter. Slektsforskere og lokalhistorikere til stede."),

    ("Nasjonalmuseets sommerutstilling 2026",
     "https://www.nasjonalmuseet.no/",
     "Frogner", "2026-06-12", "kultur",
     "Storformat-utstilling på nybygget. Tema og kurator offentliggjøres "
     "på vårparten. Barnefamilieaktiviteter hele sommeren."),

    ("Munchmuseet: Sommersesong 2026",
     "https://www.munchmuseet.no/",
     "Gamle Oslo", "2026-06-01", "kultur",
     "Sommersesongens hovedutstilling åpnes i Munchmuseet på Bjørvika. "
     "Lengre åpningstider og ekstra guidede turer gjennom sommeren."),

    ("Oslo Internasjonale Filmfestival 2026",
     "https://oslofilmfestival.com/",
     "St. Hanshaugen", "2026-10-28", "kultur",
     "Oslos eldste filmfestival. Over 150 filmer på Vega, Saga, Gimle og "
     "andre sentrumskinoer. Fra dokumentar til kunstfilm."),
    # --- Markastuer ---------------------------------------------------------
    ("Skjennungstua åpner sommersesongen",
     "https://no.wikipedia.org/wiki/Skjennungstua",
     "Nordre Aker", "2026-05-02", "arrangement",
     "Skjennungstua, Skiforeningens serveringsstue i Nordmarka nord for "
     "Sognsvann, åpner lørdags- og søndags-kafeen for sommeren. Vaffelduft "
     "og utsikt mot Skjennungen. Turstart fra Frognerseteren eller Sognsvann."),

    ("Kikutstua / Kikut (DNT-hytte)",
     "https://ut.no/hytte/10647/kikutstua",
     "Nordre Aker", "2026-05-16", "arrangement",
     "DNT Oslo og Omegn sin hytte ved Kikut i Nordmarka. Overnatting, kafe "
     "og betjent servering på helger. Populær stoppestasjon på lange "
     "skiturer og sykkelturer gjennom Nordmarka."),

    ("Mariholtet serveringsstue åpner",
     "https://mariholtet.no/",
     "Alna", "2026-04-25", "arrangement",
     "Mariholtet i Østmarka åpner vaffelkafeen for vår- og sommersesongen. "
     "Populær endestasjon på turer fra Haugerud, Oppsal og Sarabråten. "
     "Bamsen Brumm-tradisjon og skogsvandring."),

    ("Lilloseter serveringsstue",
     "https://lilloseter.no/",
     "Nordre Aker", "2026-05-02", "arrangement",
     "Lilloseter i Nordmarka — betjent stue med vafler og kaffe. "
     "Kort avstand fra Lillomarka skistadion og Solemskogen. "
     "Turstart fra Movann eller Linderudkollen."),

    ("Sinober — markastue i Lillomarka",
     "https://no.wikipedia.org/wiki/Sinober",
     "Grorud", "2026-05-16", "arrangement",
     "Sinober ligger i Lillomarka nord for Grorud — enkel markastue med "
     "servering i helgene. Turstart fra Movann eller Solemskogen. "
     "Betjent sesong fra mai."),

    ("Rustadsaga sportsstue",
     "https://no.wikipedia.org/wiki/Rustadsaga",
     "\u00d8stensj\u00f8", "2026-04-25", "arrangement",
     "Rustadsaga ved Nøklevann — serveringsstue og badeplass. "
     "Populær utgangsport for tur, jogging og bading i Østmarka. "
     "Kafeen er åpen hele sommeren."),

    ("Sandbakken sportsstue",
     "https://www.google.com/maps/search/?api=1&query=Sandbakken+sportsstue+%C3%98stmarka",
     "Nordstrand", "2026-04-25", "arrangement",
     "Sandbakken i Østmarka — sportsstue og servering. "
     "Klassisk tur-mål fra Skullerud. Påsketradisjon og sommer-kafe. "
     "Grillplass og teltområde like ved."),

    ("Kobberhaughytta",
     "https://no.wikipedia.org/wiki/Kobberhaughytta",
     "Nordre Aker", "2026-06-01", "arrangement",
     "DNT Oslo og Omegn sin betjente hytte i Nordmarka. Overnatting, "
     "middag og frokost. Kort avstand fra Blåtårn og Kikutstua."),

    # --- Svømmehaller ------------------------------------------------------
    ("Tøyenbadet — sommersesong 2026",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/toyenbadet/",
     "Gamle Oslo", "2026-05-01", "arrangement",
     "Tøyenbadet er Oslos nye store svømmehall — 50 m basseng, stupetårn, "
     "terapi- og barnebasseng. Utvidede åpningstider i sommerferien."),

    ("Frognerbadet åpner for sommeren",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/frognerbadet/",
     "Frogner", "2026-05-22", "arrangement",
     "Frognerbadet er Norges største utendørsbad. 50 m basseng, stupetårn, "
     "varmtvannsbasseng og store plener. Sesong mai–august."),

    ("Holmlia bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/holmlia-bad/",
     "Søndre Nordstrand", "2026-04-25", "arrangement",
     "Holmlia bad — 25 m basseng, barnebasseng og terapibasseng. "
     "Tilbud om svømmekurs og familiesvømming hele året."),

    ("Bøler bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/boler-bad/",
     "Østensjø", "2026-04-25", "arrangement",
     "Bøler bad — 25 m basseng med varmtvannsbasseng. "
     "Svømmeklubber og rehabilitering. Åpent hele året."),

    ("Manglerud bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/manglerud-bad/",
     "Østensjø", "2026-04-25", "arrangement",
     "Manglerud bad — svømmehall med 25 m basseng og undervisningsbasseng. "
     "Hverdagsdrift for skoler og publikum."),

    ("Furuset bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/furuset-bad/",
     "Alna", "2026-04-25", "arrangement",
     "Furuset bad — moderne anlegg med 25 m basseng, barnebasseng og "
     "stupetårn. Mye brukt av skoleklasser og svømmeklubber i Groruddalen."),

    ("Romsås bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/romsas-bad/",
     "Grorud", "2026-04-25", "arrangement",
     "Romsås bad — kombinasjonsanlegg med svømmebasseng, terapibasseng og "
     "varmtvannsbasseng. Knutepunkt i bydel Grorud."),

    ("Økern bad",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/okern-bad/",
     "Bjerke", "2026-04-25", "arrangement",
     "Økern bad — tradisjonsrik svømmehall. 25 m basseng og terapibasseng. "
     "Populært blant eldre og svømmeklubber."),


    # --- Signaturfestivaler sommer/høst 2026 -------------------------------
    ("Øyafestivalen 2026",
     "https://www.oyafestivalen.no/",
     "Gamle Oslo", "2026-08-11", "kultur",
     "Norges største musikkfestival i Tøyenparken. 11.-15. august 2026. "
     "Internasjonale og norske artister på seks scener. Arena for mat, drikke og kunst."),

    ("Oslo Pride 2026",
     "https://www.oslopride.no/",
     "Frogner", "2026-06-26", "kultur",
     "Oslos største skeive markering. Pride Park i Spikersuppa, paradeløpet "
     "gjennom sentrum og arrangementer i hele byen. 19.-27. juni 2026."),

    ("Oslo Jazzfestival 2026",
     "https://oslojazz.no/",
     "Frogner", "2026-08-17", "kultur",
     "Byens jazz-uke med konserter på Nasjonalmuseet, Sentralen, Victoria "
     "og Oslo Konserthus. Internasjonale navn og norsk toppklasse. Midten av august."),

    ("Norwegian Wood 2026",
     "https://www.norwegianwood.no/",
     "Frogner", "2026-06-13", "kultur",
     "Rockfestival på Frognerbadet i Frognerparken. Klassikere og nye navn "
     "på Oslos mest sjarmerende konsertarena. Sankthanshelgen."),

    ("MELA-festivalen 2026",
     "https://melahuset.no/",
     "St. Hanshaugen", "2026-08-22", "kultur",
     "Oslos gratis verdensmusikk-festival på Rådhusplassen. Musikk, mat og "
     "kunsthåndverk fra hele verden. Midten/slutten av august."),

    ("Kulturnatten Oslo 2026",
     "https://www.kulturnatt.no/",
     "St. Hanshaugen", "2026-09-18", "kultur",
     "Hundrevis av gratis arrangementer på museer, teatre, biblioteker og "
     "gallerier over hele Oslo. Tredje fredag i september."),

    ("Elvelangs Akerselva 2026",
     "https://www.oslo.kommune.no/",
     "Sagene", "2026-09-18", "kultur",
     "Fakkel- og lanterneopplevelse langs Akerselva på Kulturnatten. "
     "Musikk, lys og kunstinstallasjoner fra Grefsen til Vaterland."),

    ("Oslo World 2026",
     "https://osloworld.no/",
     "Gamle Oslo", "2026-10-28", "kultur",
     "Verdensmusikkfestival på Rockefeller, Kulturkirken Jakob og Cosmopolite. "
     "Artister fra Afrika, Asia, Latin-Amerika og Midtøsten. Slutten av oktober."),

    ("Oslo Bokfestival 2026",
     "https://www.oslobokfestival.no/",
     "Frogner", "2026-09-26", "kultur",
     "Litteraturfest på Litteraturhuset og Oslo Konserthus. Debatt, "
     "forfatterintervjuer og boklanseringer. Siste helg i september."),

    ("Ultima Samtidsmusikkfestival 2026",
     "https://ultima.no/nb",
     "St. Hanshaugen", "2026-09-11", "kultur",
     "Nordens største festival for samtidsmusikk. Konserter på Sentralen, "
     "Oslo Konserthus og Operaen. Andre/tredje uke i september."),

    ("Oslo Arkitekturfestival 2026",
     "https://oslobiennalen.no",
     "St. Hanshaugen", "2026-09-24", "kultur",
     "Årlig festival om arkitektur, byutvikling og design. Arrangementer "
     "på Rådhuset, DogA og Oslo Bymuseum. Sent september."),

    # --- Bydelsdager (spre på bydeler) ----------------------------------
    ("Grünerløkkadagene 2026",
     "https://www.facebook.com/grunerlokkadagene",
     "Gr\u00fcnerl\u00f8kka", "2026-06-06", "arrangement",
     "Folkefest på Olaf Ryes plass med musikk, matboder og aktiviteter. "
     "Årlig feiring av Grünerløkka. Første helg i juni."),

    ("Groruddagen 2026",
     "https://www.oslo.kommune.no/bydel-grorud/",
     "Grorud", "2026-09-05", "arrangement",
     "Årlig folkefest på Grorud torg og Romsås. Bydelens egne lag, "
     "kor og orkestre. Matboder og scene. Første lørdag i september."),

    ("Stovnerdagen 2026",
     "https://www.oslo.kommune.no/bydel-stovner/",
     "Stovner", "2026-08-29", "arrangement",
     "Stovners bydelsdag med loppemarked, matboder, scene og familieaktiviteter "
     "på Stovner senter. Siste helg i august."),

    ("Alnabyfest 2026",
     "https://www.oslo.kommune.no/bydel-alna/",
     "Alna", "2026-08-15", "arrangement",
     "Stor bydelsfest på Furuset og Lindeberg. Musikk, dans, matboder "
     "fra 30+ kulturer. Midten av august."),

    ("Holmliadagen 2026",
     "https://www.oslo.kommune.no/bydel-sondre-nordstrand/",
     "S\u00f8ndre Nordstrand", "2026-06-13", "arrangement",
     "Stor folkefest på Holmlia torg. Scene, konserter, matboder fra "
     "mange kulturer. Første/andre helg i juni."),

    ("Bjerkedagen 2026",
     "https://www.oslo.kommune.no/bydel-bjerke/",
     "Bjerke", "2026-09-12", "arrangement",
     "Bjerkes bydelsdag med aktiviteter på Linderud senter og Bjerkebanen. "
     "Første/andre helg i september."),

    ("Ullerndagen 2026",
     "https://www.oslo.kommune.no/bydel-ullern/",
     "Ullern", "2026-09-05", "arrangement",
     "Bydelsdag med lopper, kakesalg, musikk på CC Vest og Røa skole. "
     "Første lørdag i september."),

    ("Nordstranddagene 2026",
     "https://www.oslo.kommune.no/bydel-nordstrand/",
     "Nordstrand", "2026-08-29", "arrangement",
     "Bydelsdag på Lambertseter og Nordstrand. Musikk, dans, matboder og "
     "aktiviteter for barn. Slutten av august."),

    # --- Sommerarrangementer (juli tomt før) -----------------------------
    ("Piknik i Parken 2026",
     "https://piknikiparken.no/",
     "Gr\u00fcnerl\u00f8kka", "2026-06-26", "kultur",
     "Musikkfestival i Sofienbergparken. Tre dager med norsk pop/indie. "
     "Sent juni."),

    ("Lørdagsloppis Tøyen 2026",
     "https://www.facebook.com/toyentorg/",
     "Gamle Oslo", "2026-07-11", "arrangement",
     "Loppemarked på Tøyen torg hver lørdag i juli. Lokale selgere, "
     "mat og livemusikk."),

    ("Gressbaneturnering IL Try sommer 2026",
     "https://il-try.no/",
     "Vestre Aker", "2026-07-04", "idrett",
     "Try IL arrangerer sommercup med småbaner og aktiviteter for barn "
     "på Gressbanen. Trekker klubber fra hele Oslo. Første helg i juli."),

    ("Sommerball Rådhusplassen 2026",
     "https://www.oslo.kommune.no/",
     "St. Hanshaugen", "2026-07-18", "arrangement",
     "Utendørs dansetilstelning med storband på Rådhusplassen. Tilbakekomst "
     "av klassiker fra 1950-tallet. Midten av juli."),

    ("Frognerbad-sesongen 2026",
     "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/frognerbadet/",
     "Frogner", "2026-05-15", "arrangement",
     "Frognerbadet åpner for sommersesongen. Utendørs basseng, "
     "stupbrett og kafe. Åpent daglig til 1. september."),

    # --- Høst / vinter --------------------------------------------------
    ("Julemarked på Spikersuppa 2026",
     "https://www.julemarkedet.no/",
     "St. Hanshaugen", "2026-11-20", "arrangement",
     "Julemarked på Eidsvolls plass og Spikersuppa. Isbane, boder, "
     "Ferris hjul og pepperkake-by. Fra 20. november til 1. januar."),

    ("Oslo Lucia-tog 2026",
     "https://www.oslodomkirke.no/",
     "St. Hanshaugen", "2026-12-13", "kultur",
     "Tradisjonell lucia-feiring i Oslo Domkirke. Barnekor og orgel. 13. desember."),

    ("Hovedoeya kulturdag 2026",
     "https://www.hovedoya.no/",
     "Gamle Oslo", "2026-08-29", "kultur",
     "Kunstnerøyas sommerfest. Guidet tur i klosterruinene, konserter "
     "og kunstutstillinger. Siste lørdag i august."),

    # --- Sport høst 2026 (bredere dekning) -------------------------------
    ("Vaalerenga-Rosenborg 2026",
     "https://www.vif-fotball.no/",
     "Gamle Oslo", "2026-08-09", "idrett",
     "Eliteseriekamp på Intility Arena. Klassikerne VIF-RBK trekker "
     "stort publikum. Midten av august."),

    ("Lyn-Skeid 2026",
     "https://www.lynfotball.no/",
     "Vestre Aker", "2026-09-12", "idrett",
     "Bydelskamp mellom Lyn (Ullevaal) og Skeid (Nordre Aker). "
     "OBOS-ligaen. September."),

    ("Oslo Skivinter 2026",
     "https://www.skiforeningen.no/",
     "Vestre Aker", "2026-12-27", "idrett",
     "Skiforeningen åpner løypene etter julen. Garantert spor fra "
     "Frognerseteren og Sognsvann. 27. desember-start ved snø."),

    ("Bislett-stevne 2026 (Oslo Athletics Games)",
     "https://www.bislettgames.com/",
     "St. Hanshaugen", "2026-06-11", "idrett",
     "Internasjonalt friidretts-stevne på Bislett stadion. Diamond League. "
     "Andre torsdag i juni."),

    ("Oslo Løypa 2026 (skisprint)",
     "https://www.skiforeningen.no/",
     "Frogner", "2026-02-21", "idrett",
     "Bysprint på ski i sentrum. Internasjonale løpere og publikumsfest. "
     "Siste helg i februar."),

    # --- Hand-kurerte arrangementer for underdekte bydeler -----------------
    # Sagene
    ("Sagene kirke konsertserie 2026",
     "https://kirken.no/sagene",
     "Sagene", "2026-05-14", "kultur",
     "Sagene kirke har konsertserie med klassisk og kor hver torsdag "
     "kveld i mai-juni. Gratis inngang, kollekt ved utgangen."),

    ("Iladalen sommerfest 2026",
     "https://www.facebook.com/oslobyvelforening",
     "Sagene", "2026-06-13", "arrangement",
     "Bydelsfest i Iladalen park med korps, loppemarked, kakebord og "
     "leker for barn. Arrangeres av Iladalen vel andre lørdag i juni."),

    ("Bjølsen kulturkirke - jazzkveld 2026",
     "https://kulturkirken.no/",
     "Sagene", "2026-04-30", "kultur",
     "Månedlig jazzkveld i Bjølsen kulturkirke med lokale band. "
     "Siste torsdag i måneden, gratis adgang."),

    ("Sagene torgs loppemarked 2026",
     "https://www.facebook.com/Sagenetorg/",
     "Sagene", "2026-05-09", "arrangement",
     "Månedlig loppemarked på Sagene torg, andre lørdag fra mai til "
     "september. Lokale selgere, mat og live musikk."),

    # Stovner
    ("Stovner bibliotek - barnetimen 2026",
     "https://deichman.no/aktuelt",
     "Stovner", "2026-04-28", "kultur",
     "Hver tirsdag kl 11 leser bibliotekarene bøker for barn 1-5 år "
     "på Stovner bibliotek. Gratis, drop-in."),

    ("Stovner senter mat- og kulturmarked 2026",
     "https://stovnersenter.no/",
     "Stovner", "2026-05-23", "arrangement",
     "Stort utendørs marked på Stovner senter med matboder fra 30+ "
     "kulturer, dans og scene. Tredje lørdag i mai og september."),

    ("Liastua skikurs for barn 2026",
     "https://www.facebook.com/oslobyvelforening",
     "Stovner", "2026-12-12", "idrett",
     "Skiforeningen og Lia IL holder skikurs for barn 4-10 år på "
     "Liastua i Lillomarka. Andre lørdag i desember ved snøfall."),

    ("Stovner kirke - barnekor 2026",
     "https://kirken.no/stovner",
     "Stovner", "2026-05-17", "kultur",
     "Stovner kirkes barnekor opptrer på 17. mai med tradisjonelle "
     "sanger. Familiegudstjeneste fra kl 11."),

    # Bjerke
    ("Linderud julemarked 2026",
     "https://www.linderudsenter.no/",
     "Bjerke", "2026-11-28", "arrangement",
     "Tradisjonelt julemarked på Linderud senter med boder, glogg, "
     "barneaktiviteter og julenisse. Første helg i adventstiden."),

    ("Veitvet senter aktivitetsdag 2026",
     "https://www.veitvetsenter.no/",
     "Bjerke", "2026-09-19", "arrangement",
     "Høstfest på Veitvet senter med musikk, mat og leker for barn. "
     "Tredje lørdag i september."),

    ("Refstad allmenningsfest 2026",
     "https://www.facebook.com/oslobyvelforening",
     "Bjerke", "2026-08-22", "arrangement",
     "Sommerfest på Refstad allmenning med grilling, korps og "
     "fellestilstelning. Arrangeres av Refstad vel siste helg i august."),

    ("Bjerke Travbane - V75 søndag 2026",
     "https://nb-no.facebook.com/bjerketravbane/",
     "Bjerke", "2026-05-03", "idrett",
     "V75-søndager på Bjerke travbane med Norges største travløp. "
     "Familieaktiviteter, mat og publikumsadgang fra kl 12."),

    # Ullern
    ("Ullern kulturhus - kammerkonsert 2026",
     "https://www.facebook.com/ullernkulturhus/",
     "Ullern", "2026-05-09", "kultur",
     "Månedlige kammerkonserter på Ullern kulturhus med musikere fra "
     "Oslo Filharmonien. Andre lørdag i måneden."),

    ("Bestum vel sommerfest 2026",
     "https://www.facebook.com/oslobyvelforening",
     "Ullern", "2026-06-20", "arrangement",
     "Bestum vels årlige sommerfest på Bestum skole. Korps, kakesalg, "
     "tombola og leker. Tredje lørdag i juni."),

    ("Skøyen Lions loppemarked 2026",
     "https://www.lions.no/",
     "Ullern", "2026-04-25", "arrangement",
     "Skøyen Lions arrangerer loppemarked på Skøyen skole vår og høst. "
     "Inntekter går til lokale veldedige formål."),

    # --- Alpinbakker / vinterarenaer ---------------------------------------
    ("Oslo Vinterpark (Tryvann) — sesongåpning",
     "https://www.oslovinterpark.no/",
     "Marka", "2026-12-12", "idrett",
     "Oslos største alpinanlegg åpner for sesongen 2026/27. 18 nedfarter, snø-park, 13 heiser. Vanligvis åpning andre helg i desember når snøforholdene tillater."),

    ("Wyllerløkka — sesongåpning",
     "https://oslovinterpark.no/",
     "Vestre Aker", "2026-12-19", "idrett",
     "Wyllerløkka alpinanlegg ved Holmenkollen åpner for ny vintersesong. Familievennlig anlegg med skiskole, skileie og kveldskjøring."),

    ("Grefsenkollen alpinanlegg — sesongstart",
     "https://www.skiforeningen.no/",
     "Nordre Aker", "2026-12-26", "idrett",
     "Grefsenkollen alpinanlegg åpner typisk i romjulen. Bynære nedfarter med utsikt over Oslofjorden. Kveldsåpent og lysløyper i tilkobling."),

    ("Trollvann lysløype — sesongåpning",
     "https://www.facebook.com/trollvann/",
     "Nordre Aker", "2026-12-15", "idrett",
     "Lysløypa rundt Trollvann åpner for sesongen når snøen kommer. 2,5 km flat sløyfe perfekt for nybegynnere og barn. Helt opplyst om kvelden."),

    ("Linderudkollen skistadion — vintersesong",
     "https://linderudkollen.no/",
     "Bjerke", "2026-12-12", "idrett",
     "Linderudkollen skistadion i Lillomarka åpner ski- og biathlon-anlegget når snøforholdene tillater. Kunstsnø brukes ved behov. Renn og treninger."),

    # --- Ishaller / hockey-arenaer ----------------------------------------
    ("Jordal Amfi — Vålerenga Hockey sluttspill",
     "https://www.facebook.com/valerengaishockey/",
     "Gamle Oslo", "2026-04-30", "idrett",
     "Vålerenga Ishockey spiller hjemmekamper i Jordal Amfi. Sjekk kampoppsett for vårens sluttspill og høstens seriestart i september."),

    ("Manglerud Star — sesongstart hockey",
     "https://www.manglerudstar.no/",
     "Østensjø", "2026-09-15", "idrett",
     "Manglerud Star Ishall er hjemmebanen til Manglerud Star Hockey. Sesongstart i 1. divisjon i midten av september."),

    ("Furuset Forum — isidrett",
     "https://www.facebook.com/furusetishockey/",
     "Alna", "2026-09-20", "idrett",
     "Furuset Forum huser Furuset Hockey. Sesongåpning seriespill tredje helg i september. Kveldsskøyteis åpen for publikum gjennom hele sesongen."),

    # --- Klatre- og urbansport-haller -------------------------------------
    ("Klatreverket Løren",
     "https://klatreverket.no/loren/",
     "Grünerløkka", "2026-04-26", "idrett",
     "Klatreverket Løren er en av Oslos største klatresentre. Tau- og buldreklatring, kurser og barneklubber. Åpent daglig hele året."),

    ("Vulkan Klatresenter",
     "https://vulkanklatresenter.no/",
     "Grünerløkka", "2026-04-26", "idrett",
     "Klatresenter på Vulkan i Grünerløkka. Buldring og topptau, caféområde. Populært for både nybegynnere og erfarne klatrere."),

]


def load_events() -> list[dict]:
    """Returner eventene som normaliserte story-dicts.

    Viktig: `date_iso` (publiseringsdato brukt til sortering) skal ALDRI
    være i fremtiden — det ville gjort at fremtidige arrangementer alltid
    lå øverst i nyhetsfeeden. I stedet settes `date_iso` til dagens dato
    for fremtidige arrangementer, og arrangementsdatoen legges i
    `event_date` slik at UI kan rendre en egen "Hva skjer fremover"-liste
    og filtrere bort arrangementer etter at de har passert.
    """
    from datetime import date as _date, timedelta as _td
    today_str = _date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    out: list[dict] = []
    for title, url, bydel, date_iso, category, summary in EVENTS:
        # date_iso i selve EVENTS-tuppelen er event-datoen (når det skjer).
        event_date = date_iso
        # Hopp over arrangementer som har passert for mer enn 14 dager siden.
        if event_date:
            try:
                ev_d = _date.fromisoformat(event_date)
                if (_date.today() - ev_d).days > 14:
                    continue
            except ValueError:
                pass
        # Publiseringsdato = dagens dato, men aldri frem i tid.
        published_date = min(event_date, today_str)
        out.append({
            "id": _event_id(url, title),
            "bydel": bydel,
            "title": title,
            "url": url,
            "source": "Bydelsnytt kuratert",
            "source_id": "events",
            "published_iso": f"{published_date}T00:00:00+00:00",
            "date_iso": published_date,
            "event_date": event_date,
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
        print(f"  {k}: {v}")
    print()
    print("Per bydel:")
    for k, v in per_bydel.items():
        print(f"  {k}: {v}")
