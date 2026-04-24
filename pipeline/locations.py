"""Venue -> (lat, lng)-tabell for Leaflet-kart."""

VENUES = [
    # O-loep / orientering (title-based, sjekkes foerst)
    ("title_contains", "orientering: pinseloepet", 59.979, 10.686),      # Frognerseteren
    ("title_contains", "orientering: oslo 3-dagers", 59.979, 10.686),    # Frognerseteren
    ("title_contains", "orientering: km sprint", 59.925, 10.708),         # Frognerparken
    ("title_contains", "orientering: oslo cup 1", 59.976, 10.732),        # Sognsvann
    ("title_contains", "orientering: oslo cup 3", 59.878, 10.867),        # Oestmarksetra
    ("title_contains", "orientering: lillomarka", 59.975, 10.818),        # Linderudkollen
    ("title_contains", "orientering: heming", 59.983, 10.667),            # Tryvann/Holmenkollen
    ("title_contains", "orientering: koll", 59.862, 10.852),              # Skullerud
    ("title_contains", "orientering: osi", 59.942, 10.720),               # Blindern
    ("title_contains", "orientering: om langdistanse", 60.005, 10.736),   # Ullevaalseter
    ("title_contains", "orientering: om stafett", 59.862, 10.852),        # Skullerud
    ("title_contains", "orientering: fossum", 59.937, 10.580),            # Fossum/Vestmarka
    ("title_contains", "orientering: blodslitet", 59.990, 10.735),        # Nordmarka generic
    ("title_contains", "orientering: nattuglen", 59.979, 10.686),         # Frognerseteren
    ("title_contains", "orientering: o-troll", 59.976, 10.732),           # Sognsvann
    # O-loep klubber (URL-fallback)
    ("url_contains", "nydalensil.no", 59.976, 10.732),
    ("url_contains", "lillomarkaol", 59.975, 10.818),
    ("url_contains", "koll.no", 59.862, 10.852),
    ("url_contains", "osi-o.no", 59.942, 10.720),
    ("url_contains", "fossumif", 59.937, 10.580),
    ("url_contains", "eventor.orientering", 59.976, 10.732),
    # Idrettslag
    ("url_contains", "heming.no", 59.952, 10.708),
    ("url_contains", "roail.no", 59.942, 10.637),
    ("url_contains", "njard.no", 59.928, 10.705),
    ("url_contains", "kjelsaas.no", 59.967, 10.792),
    ("url_contains", "fklyn.no", 59.959, 10.761),
    ("url_contains", "il-try.no", 59.957, 10.681),  # Grindbakken skole
    ("url_contains", "rustadil.no", 59.894, 10.832),
    ("url_contains", "tryvann", 59.983, 10.667),
    ("url_contains", "vestreakerskiklub", 59.974, 10.677),
    ("url_contains", "furusetif", 59.941, 10.864),
    ("url_contains", "sageneif", 59.939, 10.761),
    ("url_contains", "grorudil", 59.961, 10.881),
    ("url_contains", "nordstrandif", 59.866, 10.786),
    ("url_contains", "nordreakerturn", 59.945, 10.765),
    ("url_contains", "monolitten", 59.925, 10.708),
    ("url_contains", "christiania", 59.925, 10.770),
    ("url_contains", "ullernif", 59.923, 10.648),
    ("url_contains", "holmliask", 59.849, 10.821),
    ("url_contains", "sthanshaugenfotball", 59.923, 10.733),
    ("url_contains", "obik.no", 59.939, 10.761),
    ("url_contains", "skiforeningen", 59.965, 10.672),
    ("url_contains", "skeid.no", 59.933, 10.751),
    ("url_contains", "vif-fotball.no", 59.916, 10.785),
    ("url_contains", "bolerif.no", 59.892, 10.830),
    # UiO / OsloMet (fiks: unngaa fallback til Nordre Aker-senter = Nydalen)
    ("url_contains", "uio.no", 59.9395, 10.7186),  # Blindern
    ("url_contains", "oslomet.no", 59.9178, 10.7356),  # Pilestredet
    # Svoemmehaller (Oslo kommunes bad)
    ("title_contains", "tøyenbadet", 59.9174, 10.7704),
    ("url_contains", "toyenbadet", 59.9174, 10.7704),
    ("title_contains", "frognerbadet", 59.9269, 10.7040),
    ("url_contains", "frognerbadet", 59.9269, 10.7040),
    ("title_contains", "holmlia bad", 59.8540, 10.8147),
    ("url_contains", "holmlia-bad", 59.8540, 10.8147),
    ("title_contains", "bøler bad", 59.8802, 10.8230),
    ("url_contains", "boler-bad", 59.8802, 10.8230),
    ("title_contains", "manglerud bad", 59.8879, 10.8175),
    ("url_contains", "manglerud-bad", 59.8879, 10.8175),
    ("title_contains", "furuset bad", 59.9421, 10.8611),
    ("url_contains", "furuset-bad", 59.9421, 10.8611),
    ("title_contains", "romsås bad", 59.9541, 10.8983),
    ("url_contains", "romsas-bad", 59.9541, 10.8983),
    ("title_contains", "økern bad", 59.9362, 10.8093),
    ("url_contains", "okern-bad", 59.9362, 10.8093),
    # Markastuer (nord i Nordmarka, oestover i Oestmarka)
    ("url_contains", "kobberhaug", 60.033, 10.728),
    ("url_contains", "ullevalseter", 60.005, 10.736),
    ("url_contains", "lilloseter", 60.015, 10.822),
    ("title_contains", "skjennungstua", 59.994, 10.714),
    ("title_contains", "kikutstua", 60.067, 10.714),
    ("title_contains", " kikut ", 60.067, 10.714),
    ("title_contains", "mariholtet", 59.973, 10.935),
    ("title_contains", "lilloseter", 60.015, 10.822),
    ("title_contains", "sinober", 59.975, 10.937),
    ("title_contains", "rustadsaga", 59.870, 10.872),
    ("title_contains", "sandbakken", 59.873, 10.884),
    ("title_contains", "kobberhaug", 60.033, 10.728),
    ("title_contains", "skjennungen", 59.994, 10.714),
    # Skoler
    ("url_contains", "gamlebyen.osloskolen", 59.903, 10.776),
    ("url_contains", "ostensjo.osloskolen", 59.895, 10.827),
    ("url_contains", "ullern.vgs", 59.921, 10.660),
    # Oslo kommune / etater
    ("url_contains", "bymiljoetaten", 59.911, 10.753),
    ("url_contains", "ruter.no/avvik", 59.910, 10.731),
    ("url_contains", "politiet.no", 59.915, 10.760),
    # Arrangements-venues
    ("url_contains", "sentrumslopet", 59.911, 10.733),
    ("url_contains", "oslomaraton", 59.911, 10.733),
    ("url_contains", "bygdoymila", 59.907, 10.686),
    ("url_contains", "grefsenkollenopp", 59.962, 10.793),
    ("url_contains", "tryvannopp", 59.983, 10.667),
    ("url_contains", "oslosbratteste", 59.983, 10.667),
    ("url_contains", "holmenkollstafetten", 59.917, 10.727),
    ("url_contains", "styrkeproven", 59.925, 10.708),
    ("url_contains", "oslograndprix", 59.911, 10.733),
    ("url_contains", "oslotri.com", 59.976, 10.732),
    ("url_contains", "oslotriathlon", 59.976, 10.732),
    ("url_contains", "norwaycup", 59.894, 10.770),
    ("url_contains", "oyafestival", 59.918, 10.775),
    ("url_contains", "musikkfest", 59.911, 10.733),
    ("url_contains", "oslopride", 59.914, 10.740),
    ("url_contains", "oslojazz", 59.917, 10.738),
    ("url_contains", "kulturnatt.oslo", 59.913, 10.739),
    ("url_contains", "infernofestival", 59.917, 10.738),
    ("url_contains", "holmenkollmarsjen", 59.965, 10.672),
    ("url_contains", "holmenkollen-skifest", 59.965, 10.672),
    ("url_contains", "sognsvannrundt", 59.976, 10.732),
    ("url_contains", "oslo.kommune.no/17-mai", 59.917, 10.727),
    # Skoler (loppemarkeder)
    ("url_contains", "ris.osloskolen", 59.953, 10.682),
    ("url_contains", "nordberg.osloskolen", 59.959, 10.743),
    ("url_contains", "tasen.osloskolen", 59.952, 10.741),
    ("url_contains", "vahl.osloskolen", 59.913, 10.763),
    ("url_contains", "ellingsrudasen.osloskolen", 59.938, 10.890),
    # Speidergrupper
    ("url_contains", "rispeiderne", 59.953, 10.682),
    ("url_contains", "nordstrandspeiderne", 59.866, 10.790),
    ("url_contains", "sagenespeiderne", 59.939, 10.761),
    ("url_contains", "norges-speiderforbund.no/gruppe/grorud", 59.961, 10.881),
    ("url_contains", "norges-speiderforbund.no/gruppe/holmlia", 59.849, 10.821),
    ("url_contains", "norges-speiderforbund.no/gruppe/grunerlokka", 59.925, 10.760),
    # Lions-klubber
    ("url_contains", "lions.no/oslonordstrand", 59.866, 10.790),
    ("url_contains", "lions.no/oslovestreaker", 59.961, 10.682),
    ("url_contains", "lions.no/oslogroruddalen", 59.961, 10.881),
    ("url_contains", "lions.no/oslogamleoslo", 59.910, 10.770),
    # Kinosaler
    ("url_contains", "vegascene", 59.920, 10.748),
    ("url_contains", "oslokino.no/kino/saga", 59.914, 10.735),
    ("url_contains", "oslokino.no/kino/colosseum", 59.930, 10.715),
    ("url_contains", "oslokino.no/kino/gimle", 59.922, 10.705),
    # Teater
    ("url_contains", "nationaltheatret", 59.914, 10.734),
    ("url_contains", "detnorsketeatret", 59.914, 10.736),
    ("url_contains", "oslonye", 59.920, 10.742),
    ("url_contains", "operaen.no", 59.907, 10.753),
    # Konsertscener
    ("url_contains", "oslokonserthus", 59.914, 10.728),
    ("url_contains", "sentrumscene", 59.916, 10.746),
    ("url_contains", "rockefeller.no", 59.915, 10.748),
    ("url_contains", "oslospektrum", 59.912, 10.753),
    ("url_contains", "jakobkulturkirke", 59.924, 10.761),
    # Deichman-filialer
    ("url_contains", "deichman.no/bjorvika", 59.909, 10.757),
    ("url_contains", "deichman.no/grunerlokka", 59.924, 10.762),
    ("url_contains", "deichman.no/toyen", 59.916, 10.777),
    ("url_contains", "deichman.no/majorstuen", 59.929, 10.716),
    ("url_contains", "deichman.no/torshov", 59.938, 10.758),
    ("url_contains", "deichman.no/lambertseter", 59.862, 10.797),
    ("url_contains", "deichman.no/furuset", 59.941, 10.864),
    ("url_contains", "deichman.no/bokstart", 59.909, 10.757),
    ("url_contains", "sommerles.no", 59.909, 10.757),
    # Kommune-venues / 17. mai-ruten / markeringer
    ("url_contains", "oslo.kommune.no/17-mai", 59.914, 10.737),
    ("url_contains", "oslo.kommune.no/mangfold", 59.913, 10.777),
    ("url_contains", "oslo.kommune.no/sankthans", 59.908, 10.696),
    ("url_contains", "oslo.kommune.no/frivillighet", 59.913, 10.733),
    ("url_contains", "oslo.kommune.no/jul", 59.914, 10.744),
    ("url_contains", "oslo.kommune.no/byarkivet", 59.931, 10.757),
    ("url_contains", "ukm.no/oslo", 59.913, 10.754),
    # Museer / film / sentrum
    ("url_contains", "filmhuset.no", 59.912, 10.742),
    ("url_contains", "nasjonalmuseet.no", 59.912, 10.729),
    ("url_contains", "munchmuseet.no", 59.907, 10.757),
    ("url_contains", "oslofilmfestival.com", 59.914, 10.738),
    ("url_contains", "operaen.no/lunsjkonserter", 59.907, 10.753),
    # Fallback: generisk deichman.no
    ("url_contains", "deichman.no", 59.909, 10.757),
]

BYDEL_CENTERS = {
    "Alna":              (59.930, 10.885),
    "Bjerke":            (59.945, 10.822),
    "Frogner":           (59.925, 10.710),
    "Gamle Oslo":        (59.910, 10.770),
    "Grorud":            (59.960, 10.878),
    "Gr\u00fcnerl\u00f8kka":       (59.925, 10.760),
    "Nordre Aker":       (59.955, 10.760),
    "Nordstrand":        (59.866, 10.790),
    "Sagene":            (59.937, 10.754),
    "St. Hanshaugen":    (59.928, 10.738),
    "Stovner":           (59.962, 10.924),
    "S\u00f8ndre Nordstrand": (59.845, 10.820),
    "Ullern":            (59.922, 10.655),
    "Vestre Aker":       (59.961, 10.682),
    "\u00d8stensj\u00f8":          (59.885, 10.828),
}


def resolve(story):
    url = (story.get("url") or "").lower()
    title = (story.get("title") or "").lower()
    source = story.get("source") or ""
    for mtype, mval, lat, lng in VENUES:
        if mtype == "url_contains" and mval in url:
            return lat, lng, True
        if mtype == "title_contains" and mval.lower() in title:
            return lat, lng, True
        if mtype == "source_equals" and mval == source:
            return lat, lng, True
    bydel = story.get("bydel")
    if bydel in BYDEL_CENTERS:
        lat, lng = BYDEL_CENTERS[bydel]
        return lat, lng, False
    return 59.913, 10.739, False


def enrich(stories):
    out = []
    for s in stories:
        lat, lng, precise = resolve(s)
        s = dict(s)
        s["lat"] = lat
        s["lng"] = lng
        s["location_precise"] = precise
        out.append(s)
    return out
