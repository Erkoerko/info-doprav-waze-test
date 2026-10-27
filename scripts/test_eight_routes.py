#!/usr/bin/env python3
"""Info doprav: manual Waze route diagnostic for the eight registered directions.
This only prints diagnostic data to GitHub Actions; it never publishes or saves traffic results.
The route-passing check is intentionally NOT implemented: real geometry/waypoint verification
is required before using any travel time for a traffic alert.
Reference geography: Info_doprav_register_tras.md, 26 Oct 2026, © OSM contributors (ODbL).
"""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from pywaze.route_calculator import WazeRouteCalculator

# Registered *direction-specific* start and end coordinates, (lat, lon).
# Intermediate checkpoints are listed for subsequent geometry validation,
# but pywaze's tested calc_routes() call only uses start and end coordinates.
ROUTES = [
    ("ST-BA-D2", "Stupava → Bratislava-Lamač", "D2",
     (48.2730342, 17.0323731), (48.1949732, 17.0435265),
     [(48.2502663,17.0209215),(48.2284594,17.0232698)]),
    ("BA-ST-D2", "Bratislava-Lamač → Stupava", "D2",
     (48.1949976,17.0437109), (48.2730342,17.0323731),
     [(48.2285066,17.0234375),(48.2502663,17.0209215)]),
    ("PK-BA-502", "Pezinok → Bratislava-Rača", "502",
     (48.2807493,17.2605122), (48.1999826,17.1479243),
     [(48.2682682,17.2412557),(48.2489949,17.2122937),(48.2295592,17.1953994)]),
    ("BA-PK-502", "Bratislava-Rača → Pezinok", "502",
     (48.1999258,17.1480753), (48.2807493,17.2605122),
     [(48.2294863,17.1956079),(48.2489318,17.2124036),(48.2681947,17.2412897)]),
    ("SC-BA-D1", "Senec → Bratislava-D1", "D1",
     (48.2240728,17.3835125), (48.1788400,17.1920305),
     [(48.2300528,17.3756021),(48.2146696,17.3002951),(48.1992796,17.2276434)]),
    ("BA-SC-D1", "Bratislava-D1 → Senec", "D1",
     (48.1787464,17.1921416), (48.2240728,17.3835125),
     [(48.1991956,17.2277829),(48.2145615,17.3002834),(48.2300528,17.3756021)]),
    ("SA-BA-R7", "Šamorín → Bratislava-Nivy", "R7",
     (48.0298858,17.3098596), (48.1337600,17.1585672),
     [(48.0553906,17.2863751),(48.0683987,17.2592930),(48.0840730,17.2247232)]),
    ("BA-SA-R7", "Bratislava-Nivy → Šamorín", "R7",
     (48.1339966,17.1576793), (48.0298858,17.3098596),
     [(48.0839744,17.2246479),(48.0683038,17.2591664),(48.0553906,17.2863751)]),
]

def point(value):
    return f"{value[0]:.7f},{value[1]:.7f}"

def road_label_match(road_names, expected):
    # Very weak plausibility check, not a verification of the full route.
    text = " | ".join(str(n) for n in road_names)
    return expected.lower() in text.lower()

async def main():
    ts = datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds")
    print(f"INFO DOPRAV – EIGHT DIRECTION ROUTE DIAGNOSTIC, {ts}", flush=True)
    print("TEST_ONLY=true PUBLIC_PUBLISHING=false GEOMETRY_CHECK=false", flush=True)
    print("For each returned alternative, road names are illustrative, NOT route verification.", flush=True)
    successful = 0
    async with WazeRouteCalculator(region="EU") as waze:
        for route_id, title, expected, start, end, checkpoints in ROUTES:
            print(f"\n=== {route_id} | {title} | expected road {expected} ===", flush=True)
            print(f"start={point(start)} end={point(end)} checkpoints={len(checkpoints)} (NOT ENFORCED)", flush=True)
            try:
                alternatives = await waze.calc_routes(
                    point(start), point(end), alternatives=2, real_time=True
                )
                if not alternatives:
                    print("NO_ROUTE; publishing prohibited", flush=True)
                    continue
                successful += 1
                for index, option in enumerate(alternatives, 1):
                    roads = list(getattr(option, "street_names", []) or [])
                    plausible = road_label_match(roads, expected)
                    print(
                        f"ALT={index} minutes={option.duration:.1f} "
                        f"km={option.distance:.1f} road_label_present={plausible} "
                        f"status=UNVERIFIED",
                        flush=True,
                    )
                    print(f"route_name={getattr(option, 'name', '')}", flush=True)
                    print(f"roads={roads}", flush=True)
            except Exception as exc:
                print(f"ERROR={type(exc).__name__}: {str(exc)[:300]}", flush=True)
    print(f"\nSUMMARY directions_with_response={successful}/8; GEOMETRY_UNVERIFIED", flush=True)
    if not successful:
        raise RuntimeError("Waze returned no usable route in any direction")

if __name__ == "__main__":
    asyncio.run(main())
