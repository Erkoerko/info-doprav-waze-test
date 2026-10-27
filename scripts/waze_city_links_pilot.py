"""Manual diagnostic of eight new Bratislava edge-to-centre links.
Uses original boundary profiles from Info doprav registry, and an unapproved
common centre *pilot* coordinate previously used in a successful Waze test.
No scheduled requests, API keys, storage, notifications, or publishing.
Results are never marked route verified. Pilot centre anchoring must be
confirmed in BOTH directions before any public use.
"""
import asyncio
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from pywaze.route_calculator import WazeRouteCalculator

from waze_endpoint_pilot import ENDPOINTS, compute_metrics, as_coords

# Previous successful Palisády destination from test #1; centre proxy ONLY.
CENTRE = (48.1486, 17.1077)
AREA_CODES = ("D2-LAMAC", "502-RACA", "D1-GALVANIHO", "R7-NIVY")


def city_links():
    links = []
    for ix, tag in zip(range(0, 8, 2), AREA_CODES):
        incoming, outgoing = ENDPOINTS[ix], ENDPOINTS[ix + 1]
        # Incoming original route ends at the correct Bratislava entrance lane.
        inbound_edge = incoming[4]
        # Outgoing original route starts at its own lane in Bratislava.
        outbound_edge = outgoing[3]
        links.append((f"BA-{tag}-CENTRUM", f"{tag} → centrum",
                      inbound_edge, CENTRE))
        links.append((f"CENTRUM-BA-{tag}", f"centrum → {tag}",
                      CENTRE, outbound_edge))
    return links


async def main():
    print("INFO DOPRAV – CITY LINKS MANUAL PILOT", flush=True)
    print("timestamp=" + datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true PUBLISH=false SCHEDULE=false")
    print(f"CENTRE_PROVISIONAL={as_coords(CENTRE)} Palisady; direction-dependent road access NOT VERIFIED")
    print("All route alternatives and current vs non-live values are diagnostic, NOT traffic alerts.")
    successful = 0
    async with WazeRouteCalculator(region="EU") as waze:
        for route_id, label, start, end in city_links():
            print(f"\n=== {route_id} {label} ===", flush=True)
            print(f"START={as_coords(start)} END={as_coords(end)}", flush=True)
            try:
                raw_routes = await waze.get_routes(
                    waze.coords_string_parser(as_coords(start)),
                    waze.coords_string_parser(as_coords(end)),
                    alternatives=2,
                )
                if not raw_routes:
                    print("NO_ROUTES status=UNVERIFIED", flush=True)
                    continue
                successful += 1
                for n, raw in enumerate(raw_routes, 1):
                    try:
                        metrics = compute_metrics(raw)
                    except (ValueError, KeyError, TypeError) as exc:
                        print(f"ALT={n} BAD_RESPONSE {str(exc)[:120]}", flush=True)
                        continue
                    name = raw.get("routeName", "")
                    roads = [str(v) for v in raw.get("streetNames", []) if v]
                    print(f"ALT={n} minutes={metrics['minutes']} km={metrics['km']} "
                          f"non_live={metrics['non_live_minutes']} "
                          f"free_flow={metrics['free_flow_minutes']} "
                          f"delta={metrics['delta_min']:+.1f} "
                          f"name={name!r} STATUS=UNVERIFIED", flush=True)
                    print(f"ROADS={roads}", flush=True)
            except Exception as exc:
                print(f"ERROR {type(exc).__name__}: {str(exc)[:180]}", flush=True)
    print(f"\nSUMMARY response_directions={successful}/8, VERIFIED=0, SENT=0", flush=True)
    if successful == 0:
        raise RuntimeError("All city link measurements failed")


if __name__ == "__main__":
    asyncio.run(main())
