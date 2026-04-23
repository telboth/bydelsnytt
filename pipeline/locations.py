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
    ("url_contains", "nydalensil.no", 59.976, 10.732),                    # Sognsvann/Nydalen
    ("url_contains", "lillomarkaol", 59.975, 10.818),                     # Linderudkollen
    ("url_contains", "koll.no", 59.862, 10.852),                          # Skullerud
    ("url_contains", "osi-o.no", 59.942, 10.720),                         # Blindern
    ("url_contains", "fossumif", 59.937, 10.580),                         # Fossum
    ("url_contains", "eventor.orientering", 59.976, 10.732),              # Sognsvann (generisk)
    # Idrettslag
    ("url_contains", "heming.no", 59.952, 10.708),
    ("url_contains", "roail.no", 59.942, 10.637),
    ("url_contains", "njard.no", 59.928, 10.705),
    ("url_contains", "kjelsaas.no", 59.967, 10.792),
    ("url_contains", "fklyn.no", 59.959, 10.761),
    ("url_contains", "il-try.no", 59.948, 10.680),  # Gressbanen / Slemdal
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
    # Markastuer
    ("url_contains", "kobberhaug", 60.033, 10.728),
    ("url_contains", "ullevalseter", 60.005, 10.736),
    ("url_contains", "lilloseter", 60.015, 10.822),
    # Skoler
    ("url_contains", "gamlebyen.osloskolen", 59.903, 10.776),
    ("url_contains", "ostensjo.osloskolen", 59.895, 10.827),
    ("url_contains", "ullern.vgs", 59.921, 10.660),
    # Oslo kommune / etater
    ("url_contains", "bymiljoetaten", 59.911, 10.753),
    ("url_contains", "ruter.no/avvik", 59.910, 10.731),   # Jernbanetorget - kollektivknutepunkt
    ("url_contains", "politiet.no", 59.915, 10.760),      # Oslo politihus, Gr\u00f8nlandsleiret
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
    ("url_contains", "detnorsketeatret", 59.914,