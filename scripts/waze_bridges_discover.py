"""Manual OSM bridge discovery and Waze route probe for Bratislava.

Scope: Most SNP, Most Apollo, Pristavny most, each road direction only if an
OSM motorcar bridge way is discovered. Endpoints sampled from real road geometry,
not estimated from bridge centre. Uses exactly one Overpass data request, then
up to six Waze probes. No stored traffic data, publishing, or scheduler.

IMPORTANT: These measurements cover bridge deck only. Approaches to bridges
must be defined and verified in a later revision for meaningful queue detection.
The Waze route MUST mention the requested bridge and be short to be a candidate.
All results remain UNVERIFIED until Waze road directions are visually reviewed.

© OpenStreetMap contributors, ODbL: https://www.openstreetmap.org/copyright
"""
import asyncio
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from pywaze.route_calculator import WazeRouteCalculator
from waze_endpoint_pilot import as_coords, compute_metrics
from city_route_assessment import normalize

OVERPASS = "https://overpass-api.de/api/interpreter"
# Small bbox covering all three central automobile bridges, NOT all Bratislava.
BOUNDING_BOX = (48.115, 17.075, 48.158, 17.180)
BRIDGES = {
    "SNP": ("most snp", "novy most", "most slovenskeho narodneho povstania"),
    "APOLLO": ("most apollo",),
    "PRISTAVNY": ("pristavny most",),
}
EXCLUDED_HIGHWAYS = {"footway", "path", "cycleway", "pedestrian", "steps", "bridleway", "platform"}
MAX_ROUTE_KM = 3.5
MIN_WAY_M = 220


def road_bridge_way_tags(element):
    tags = element.get("tags") or {}
    highway = tags.get("highway")
    if not highway or highway in EXCLUDED_HIGHWAYS:
        return False
    if tags.get("motor_vehicle") in ("no", "private") or tags.get("motorcar") in ("no", "private"):
        return False
    if tags.get("access") in ("no", "private"):
        return False
    bridge = tags.get("bridge", "")
    return bridge not in ("no", "false", "")


def route_name_bridge(element):
    tags = element.get("tags") or {}
    labels = [normalize(tags.get("name", "")), normalize(tags.get("alt_name", "")),
              normalize(tags.get("official_name", ""))]
    for key, patterns in BRIDGES.items():
        if any(term in name for name in labels for term in patterns):
            return key
    return None


def distance_m(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    q = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 12742000 * math.asin(min(1, math.sqrt(q)))


def usable_candidates(elements):
    out = {code: [] for code in BRIDGES}
    for item in elements:
        if item.get("type") != "way" or not road_bridge_way_tags(item):
            continue
        label = route_name_bridge(item)
        if label is None:
            continue
        coords = item.get("geometry") or []
        try:
            points = [(float(x["lat"]),float(x["lon"])) for x in coords]
        except (TypeError,KeyError,ValueError):
            continue
        if len(points) < 2:
            continue
        # A complete bridge can be split across many OSM ways. These are
        # candidates, not a guarantee of bank-to-bank coverage.
        total = sum(distance_m(a,b) for a,b in zip(points,points[1:]))
        if total < MIN_WAY_M:
            continue
        tags = item.get("tags") or {}
        out[label].append({
            "osm_way_id": item.get("id"),
            "bridge": label,
            "length_m": round(total),
            "points": points,
            "oneway": tags.get("oneway", ""),
            "highway": tags.get("highway", ""),
            "name": tags.get("name", ""),
        })
    return out


def endpoint_options(ways):
    """Prefer distinct OSM carriageways, avoid guessing the reverse of oneway."""
    by_direction = {}
    for way in sorted(ways,key=lambda w:w["length_m"],reverse=True):
        if len(way["points"]) < 2:
            continue
        a,b = way["points"][0],way["points"][-1]
        # Central Danube automobile bridges connect the north and south banks.
        direction = "N_TO_S" if a[0] > b[0] else "S_TO_N"
        if direction not in by_direction:
            by_direction[direction] = {
                "osm_way_id":way["osm_way_id"],
                "start":a,"end":b,"distance_m":way["length_m"],
                "name":way["name"],"oneway":way["oneway"],
            }
        # A true bidirectional bridge road can also support the opposite
        # direction, but the later Waze check still has to show correct bridge.
        if way["oneway"] in ("no","0","false","") and way["highway"] not in ("motorway", "motorway_link"):
            reverse = "S_TO_N" if direction == "N_TO_S" else "N_TO_S"
            if reverse not in by_direction:
                by_direction[reverse] = {
                    "osm_way_id":way["osm_way_id"],
                    "start":b,"end":a,"distance_m":way["length_m"],
                    "name":way["name"],"oneway":"no",
                }
    return by_direction


def expected_bridge_in_waze(bridge, route_name, street_names):
    words = " | ".join(normalize(x) for x in [route_name,*street_names])
    return any(tag in words for tag in BRIDGES[bridge])


def fetch_osm_bridges():
    south,west,north,east = BOUNDING_BOX
    q = (
        f'[out:json][timeout:25];'
        f'way["highway"]["bridge"]( {south},{west},{north},{east} );'
        'out geom;'
    )
    body=urllib.parse.urlencode({"data":q}).encode("utf-8")
    req=urllib.request.Request(OVERPASS,data=body,method="POST",
                               headers={"User-Agent":"InfoDopravResearch/0.1 manual-OSM-pilot",
                                        "Content-Type":"application/x-www-form-urlencoded",
                                        "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as response:
        payload=json.loads(response.read().decode("utf-8"))
    return usable_candidates(payload.get("elements",[]))


async def main():
    print("INFO DOPRAV – THREE BRIDGES (MANUAL DISCOVERY)")
    print("time=" + datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true PUBLIC=false RECURRING=false BRIDGE_APPROACHES=false")
    print("Source OSM © OpenStreetMap contributors; resulting GPS points are UNVERIFIED.")
    try:
        candidates=fetch_osm_bridges()
    except Exception as error:
        print(f"OSM_ERROR {type(error).__name__}: {str(error)[:200]}")
        print("SUMMARY OSM_FAILED=TRUE, WAZE_CALLS=0")
        raise RuntimeError("OSM bridge positions could not be determined") from error

    requests_count=0
    async with WazeRouteCalculator(region="EU") as waze:
        for bridge in BRIDGES:
            ways=candidates[bridge]
            options=endpoint_options(ways)
            print(f"\n=== {bridge} matching_motorway_bridge_ways={len(ways)} "
                  f"directions={list(options)} ===")
            for direction in ("N_TO_S","S_TO_N"):
                if direction not in options:
                    print(f"  {direction}: NO_OSM_DIRECTION, no Waze request")
                    continue
                start=options[direction]["start"]
                end=options[direction]["end"]
                print(f"  {direction} way={options[direction]['osm_way_id']} "
                      f"start={as_coords(start)} end={as_coords(end)}")
                requests_count+=1
                try:
                    raw=await waze.get_routes(
                        waze.coords_string_parser(as_coords(start)),
                        waze.coords_string_parser(as_coords(end)),
                        alternatives=2)
                except Exception as error:
                    print(f"  WAZE_ERROR {type(error).__name__}: {str(error)[:160]}")
                    continue
                for n, route in enumerate(raw or [],1):
                    street_names=[str(s) for s in route.get("streetNames",[]) if s]
                    name=route.get("routeName","")
                    match=expected_bridge_in_waze(bridge,name,street_names)
                    try:
                        info=compute_metrics(route)
                    except (KeyError,TypeError,ValueError) as error:
                        print(f"  ALT={n} INVALID_TIME {str(error)[:120]}")
                        continue
                    plausibility=match and info["km"] <= MAX_ROUTE_KM
                    print(f"  ALT={n} time_min={info['minutes']} distance_km={info['km']} "
                          f"bridge_label_found={match} short_route={info['km']<=MAX_ROUTE_KM} "
                          f"STATUS={'PROVISIONAL_UNVERIFIED' if plausibility else 'REVIEW_OR_REJECT'} "
                          f"name={name!r}")
                    print(f"  ROADS={street_names}")
    print(f"\nSUMMARY WAZE_REQUESTS={requests_count} MAX_ALLOWED=6 VERIFIED=0 PUBLISHED=0")


if __name__=="__main__":
    asyncio.run(main())
