"""Info doprav – BRATISLAVA BRIDGE APPROACH PILOT (MANUAL ONLY).

Given six deck crossings which succeeded on 27 October 2026 at 10:17,
select provisional approach endpoints from real OSM road nodes, about
0.7–1.7 km beyond each bank, and request Waze route times for each.
Neither calculated endpoints nor routes are production-approved. The
detector reports and rejects obvious wrong bridge choices.

NO scheduler, Telegram, output archive, secrets, paid API or retries.
One OSM Overpass request; at most six Waze routing requests. D1 motorway
endpoints and SNP one-way approaches must match legal direction as well as proximity.
© OpenStreetMap contributors (ODbL): https://osm.org/copyright
"""
import asyncio
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from pywaze.route_calculator import WazeRouteCalculator
from waze_endpoint_pilot import as_coords, compute_metrics
from waze_bridges_discover import BRIDGES, normalize, distance_m

OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = (48.117, 17.075, 48.159, 17.184)

# Direction-specific deck coordinates from the successful OSM/Waze diagnostic.
# Format: (start on bridge, end on bridge, expected approach road before,
#          expected departure road after, originating OSM way).
DECK = {
 "SNP": {
  "N_TO_S": ((48.1400244,17.1043882),(48.1369778,17.1045356),
             ("staromestska",),("panonska",),34325343),
  "S_TO_N": ((48.1369701,17.1046639),(48.1395794,17.1045399),
             ("panonska",),("staromestska",),25737798),
 },
 "APOLLO": {
  "N_TO_S": ((48.1406376,17.1290921),(48.1373201,17.1280204),
             ("kosicka", "pribinova"),("dolnozemska","einsteinova"),1147196265),
  "S_TO_N": ((48.1343521,17.1281191),(48.1406014,17.1292109),
             ("dolnozemska","einsteinova"),("kosicka", "pribinova"),59577497),
 },
 "PRISTAVNY": {
  "N_TO_S": ((48.1368599,17.1426615),(48.1324385,17.1365996),
             ("d1",),("d1",),4564634),
  "S_TO_N": ((48.1326946,17.1372745),(48.1372654,17.1434348),
             ("d1",),("d1",),4564633),
 },
}
DRIVABLE = {"motorway","motorway_link","trunk","trunk_link","primary",
            "primary_link","secondary","secondary_link","tertiary",
            "tertiary_link","unclassified","residential"}
MAX_ENDPOINT_ROAD_KM = 9.0
MAX_DETOUR_FACTOR = 2.2
MAX_DETOUR_EXTRA_KM = 2.2
MIN_ONEWAY_ALIGNMENT = 0.30
MIN_APPROACH_M = 650
MAX_APPROACH_M = 1700
TARGET_APPROACH_M = 1100

def fetch_approach_roads():
    south,west,north,east=BBOX
    box=f"({south},{west},{north},{east})"
    # Query only specifically named approach roads or ref D1: bounded traffic.
    q=(" [out:json][timeout:30];("
       f'way["highway"]["name"~"Staromestská|Panónska|Košická|Pribinova|Dolnozemská|Einsteinova",i]{box};'
       f'way["highway"]["ref"~"D1",i]{box};'
       ");out geom;")
    req=urllib.request.Request(
        OVERPASS, data=urllib.parse.urlencode({"data":q}).encode(),
        method="POST", headers={"User-Agent":"InfoDoprav/0.2 manual-test",
          "Content-Type":"application/x-www-form-urlencoded",
          "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as response:
        body=json.loads(response.read().decode())
    return body.get("elements",[])

def is_car_road(tags):
    if tags.get("highway") not in DRIVABLE:
        return False
    for key in ("access","vehicle","motor_vehicle","motorcar"):
        if tags.get(key) in ("no","private"):
            return False
    return True

def matching_name(tags, allowed):
    labels=" ".join(normalize(tags.get(k,""))
                    for k in ("name","ref","official_name","alt_name"))
    return any(token in labels for token in allowed)

def local_vectors(point, origin):
    # Vector origin -> point in metres (x east, y north).
    dy=(point[0]-origin[0])*111195
    dx=(point[1]-origin[1])*111195*math.cos(math.radians(origin[0]))
    return dx,dy

def way_direction_alignment(way, node_index, deck_start, deck_end):
    """Projected alignment of OSM way driving direction with bridge travel.

    This is a *lane hint*, not turn-by-turn connectivity verification.
    Motorway is assumed oneway unless explicitly marked otherwise; reversed
    ('-1') OSM ways run against the stored node sequence.
    """
    tags = way.get("tags") or {}
    nodes = way.get("geometry") or []
    if len(nodes) < 2:
        return None
    try:
        def pt(k):
            return (float(nodes[k]["lat"]), float(nodes[k]["lon"]))
        start_node = pt(max(0, node_index - 1))
        end_node = pt(min(len(nodes) - 1, node_index + 1))
        vx, vy = local_vectors(end_node, start_node)
        dx, dy = local_vectors(deck_end, deck_start)
        denom = math.hypot(vx, vy) * math.hypot(dx, dy)
        if denom < 1:
            return None
        alignment = (vx * dx + vy * dy) / denom
        tag = str(tags.get("oneway", "")).lower()
        if tag == "-1":
            alignment = -alignment
        elif tag in ("no", "0", "false"):
            alignment = abs(alignment)
        elif tag in ("yes", "1", "true") or tags.get("highway") == "motorway":
            pass
        else:
            # For an unmarked road, its OSM point order does not necessarily
            # express legal direction; cannot use it for a strict decision.
            return None
        return alignment
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def choose_node(elements, deck_start, deck_end, bank_side, roads, strict_direction=False):
    # Choose on the outward extension of the relevant end of bridge, not
    # an arbitrary nearest motorway ramp or wrong-lane point.
    if bank_side=="BEFORE":
        bank, other=deck_start, deck_end
    else:
        bank, other=deck_end, deck_start
    out_x,out_y=local_vectors(bank,other)
    out_len=math.hypot(out_x,out_y)
    if out_len<25:
        return None
    ex,ey=out_x/out_len,out_y/out_len
    choices=[]
    for way in elements:
        tags=way.get("tags") or {}
        if way.get("type")!="way" or not is_car_road(tags) or not matching_name(tags,roads):
            continue
        for node_index, node in enumerate(way.get("geometry") or []):
            try:
                candidate=(float(node["lat"]),float(node["lon"]))
            except (KeyError,ValueError,TypeError):
                continue
            x,y=local_vectors(candidate,bank)
            radius=math.hypot(x,y)
            if not MIN_APPROACH_M <= radius <= MAX_APPROACH_M:
                continue
            # Require candidate to lie reasonably outward along bridge axis.
            axial=(x*ex+y*ey)
            if axial/radius < 0.60:
                continue
            heading = way_direction_alignment(way, node_index, deck_start, deck_end)
            if strict_direction and (heading is None or heading < MIN_ONEWAY_ALIGNMENT):
                # Do not choose the D1 carriageway which would require a long
                # motorway U-turn just to reach the bridge in this direction.
                continue
            score=abs(radius-TARGET_APPROACH_M)+0.75*abs(radius-axial)
            if strict_direction:
                score += 80*(1-heading)
            choices.append((score, candidate, way.get("id"),tags.get("name",""),
                            tags.get("ref",""),round(radius),heading))
    if not choices:
        return None
    _,coord,way_id,name,ref,radius,heading=min(choices,key=lambda c:c[0])
    return {"coord":coord,"osm_way_id":way_id,"road":name or ref,
            "metres_from_deck":radius,
            "oneway_alignment":round(heading,2) if heading is not None else None}

def approach_directness(start, end, routed_km):
    """Reject absurd motorway loops in a proposed short bridge approach."""
    direct_km=distance_m(start,end)/1000.0
    factor=routed_km/direct_km if direct_km>0 else float("inf")
    ok=(direct_km>0 and routed_km<=MAX_ENDPOINT_ROAD_KM and
        factor<=MAX_DETOUR_FACTOR and routed_km-direct_km<=MAX_DETOUR_EXTRA_KM)
    return ok, direct_km, factor


def bridge_in_names(bridge,route):
    texts=[route.get("routeName",""),*(route.get("streetNames") or [])]
    joined=" | ".join(normalize(t) for t in texts)
    expected=any(key in joined for key in BRIDGES[bridge])
    other=any(any(key in joined for key in patterns)
              for br,patterns in BRIDGES.items() if br!=bridge)
    return expected,other

async def main():
    print("BRATISLAVA BRIDGE APPROACH PILOT",flush=True)
    print("time="+datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true PUBLISH=false SCHEDULE=false APPROACHES_UNVERIFIED=true")
    try:
        elements=fetch_approach_roads()
    except Exception as exc:
        print(f"OSM_FAILED {type(exc).__name__} {str(exc)[:160]}")
        raise
    print(f"OSM_MATCHED_WAYS={len(elements)}")
    completed=0
    async with WazeRouteCalculator(region="EU") as waze:
        for bridge, directions in DECK.items():
            for direction,(deck_start,deck_end,before,after,way_id) in directions.items():
                print(f"\n== {bridge} {direction}, reference OSM bridge way {way_id} ==")
                origin=choose_node(elements,deck_start,deck_end,"BEFORE",before,
                                   strict_direction=(bridge in ("SNP","PRISTAVNY")))
                destination=choose_node(elements,deck_start,deck_end,"AFTER",after,
                                        strict_direction=(bridge in ("SNP","PRISTAVNY")))
                print(f"APPROACH_START={origin}")
                print(f"APPROACH_END={destination}")
                if origin is None or destination is None:
                    print("NOT_MEASURABLE: no plausible OSM approach node; no Waze call")
                    continue
                start,end=origin["coord"],destination["coord"]
                if distance_m(start,end)<900:
                    print("NOT_MEASURABLE: endpoints too close")
                    continue
                try:
                    routes=await waze.get_routes(
                        waze.coords_string_parser(as_coords(start)),
                        waze.coords_string_parser(as_coords(end)),
                        alternatives=2)
                except Exception as exc:
                    print(f"WAZE_FAILED {type(exc).__name__} {str(exc)[:130]}")
                    continue
                completed+=1
                for index,option in enumerate(routes or [],1):
                    match,other=bridge_in_names(bridge,option)
                    try:
                        metrics=compute_metrics(option)
                    except (ValueError,KeyError,TypeError) as exc:
                        print(f"ALT={index} BAD_METRICS {str(exc)[:130]}")
                        continue
                    direct_approach,direct_km,length_ratio=approach_directness(
                        start,end,metrics["km"])
                    valid=match and not other and direct_approach
                    print(f"ALT={index} min={metrics['minutes']} km={metrics['km']} "
                          f"non_live={metrics['non_live_minutes']} "
                          f"delay_min={metrics['delta_min']} delay_pct={metrics['delta_pct']} "
                          f"bridge_seen={match} another_bridge_seen={other} "
                          f"straight_line_km={direct_km:.2f} "
                          f"detour_factor={length_ratio:.2f} "
                          f"approach_directness_ok={direct_approach} "
                          f"candidate={valid} verified=false",flush=True)
                    print("ROADS="+str(option.get("streetNames")),flush=True)
    print(f"\\nSUMMARY probes_with_response={completed}/6 APPROVED=0 PUBLISHED=0")
    if completed==0:
        raise RuntimeError("No provisional bridge approach endpoints worked")

if __name__=="__main__":
    asyncio.run(main())
