"""Offline helpers for Waze city-link diagnostics.

Only interprets a single Waze response. No HTTP, no publication, no persistent
storage. Route labels do not prove exact geometry. A family/road fingerprint
is a conservative identity hint for later repeated-measurement comparisons.
"""
import hashlib
import unicodedata

LANDMARKS = (
    ("MOST_SNP", ("most snp", "novy most", "most slovenskeho narodneho povstania")),
    ("MOST_APOLLO", ("most apollo",)),
    ("PRISTAVNY_MOST", ("pristavny most",)),
    ("MOST_LAFRANCONI", ("most lafranconi", "most lanfranconi")),
    ("LUZNY_MOST", ("luzny most",)),
    ("PRAZSKA", ("prazska",)),
    ("MUDRONOVA", ("mudronova",)),
    ("RACIANSKA", ("racianska",)),
    ("PIONIERSKA", ("pionierska",)),
    ("MYTNA", ("mytna",)),
    ("SANCOVA", ("sancova",)),
    ("TRNAVSKA", ("trnavska",)),
    ("VAJNORSKA", ("vajnorska",)),
    ("NABREZIE", ("nabrezie",)),
    ("PRIEVOZSKA", ("prievozska",)),
    ("MLYNSKE_NIVY", ("mlynske nivy",)),
    ("BAJKALSKA", ("bajkalska",)),
    ("EINSTEINOVA", ("einsteinova",)),
    ("GAGARINOVA", ("gagarinova",)),
    ("STAROMESTSKA", ("staromestska",)),
)

def normalize(label):
    decomp = unicodedata.normalize("NFKD", str(label)).casefold()
    return " ".join("".join(ch for ch in decomp if not unicodedata.combining(ch)).split())

def travel_family(roads):
    found = []
    for item in roads:
        text = normalize(item)
        for code, keywords in LANDMARKS:
            if any(needle in text for needle in keywords) and code not in found:
                found.append(code)
    return found if found else ["UNCLASSIFIED"]

def route_fingerprint(roads):
    joined = "|".join(normalize(s) for s in roads if s)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12] if joined else "NO_LABELS"

def is_restricted(raw):
    try:
        if int(raw.get("minPassengers") or 0) > 0:
            return True
    except (ValueError, TypeError):
        return True
    attrs = raw.get("routeAttr") or []
    if isinstance(attrs, str):
        attrs = [attrs]
    return any("HOV" in str(a).upper() for a in attrs)

def select_fastest(alts, metrics_parser):
    """Choose fastest unrestricted alternative, with its own reference.

    Caller should NOT average time or reference across the alternatives.
    Returns (index starting at 1, raw object, metric dict, human tags, digest)
    or None when no complete and unrestricted alternative exists.
    """
    scored = []
    for index, raw in enumerate(alts or [], 1):
        if not isinstance(raw, dict) or is_restricted(raw):
            continue
        try:
            metrics = metrics_parser(raw)
        except (KeyError, ValueError, TypeError):
            continue
        roads = [str(n) for n in raw.get("streetNames", []) if n]
        if not roads:
            continue
        scored.append((index, raw, metrics, travel_family(roads),
                       route_fingerprint(roads)))
    return min(scored, key=lambda row: (row[2]["minutes"], row[2]["km"])) if scored else None

def comparison_status(previous_family, previous_signature, selected):
    """Fail closed if the travel family changes between consecutive samples."""
    if selected is None:
        return "NO_ROUTE"
    if previous_family is None or previous_signature is None:
        return "FIRST_SAMPLE"
    _, _, _, family, signature = selected
    if tuple(family) != tuple(previous_family):
        return "ROUTE_FAMILY_CHANGED"
    if signature != previous_signature:
        return "ROAD_LABELS_CHANGED_REVIEW"
    return "ROAD_LABELS_STABLE_NOT_GEOMETRY_VERIFIED"
