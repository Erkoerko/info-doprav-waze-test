"""Info doprav: endpoint-only pilot for 8 fixed directions (manual run).

Exactly two coordinates are sent to routing for each directional route.
No checkpoint/geometry gate. A short road-name and distance safeguard detects
obvious reroutes; therefore results are NOT guaranteed to describe one identical
route every time.

No publishing, tokens, triggers, storage, or paid API.
Route coordinates: original project register, © OpenStreetMap contributors.
Reference kilometers: initial Waze diagnostic at 2026-10-27 02:00 Europe/Bratislava.
"""
import asyncio
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from pywaze.route_calculator import WazeRouteCalculator

# (id, description, expected corridor, start (lat, lon), end, first-test km)
ENDPOINTS = [
    ("ST-BA-D2", "Stupava → Bratislava-Lamač", "D2",
     (48.2730342, 17.0323731), (48.1949732, 17.0435265), 11.0),
    ("BA-ST-D2", "Bratislava-Lamač → Stupava", "D2",
     (48.1949976, 17.0437109), (48.2730342, 17.0323731), 10.7),
    ("PK-BA-502", "Pezinok → Bratislava-Rača", "502",
     (48.2807493, 17.2605122), (48.1999826, 17.1479243), 12.9),
    ("BA-PK-502", "Bratislava-Rača → Pezinok", "502",
     (48.1999258, 17.1480753), (48.2807493, 17.2605122), 12.8),
    ("SC-BA-D1", "Senec → Bratislava-D1", "D1",
     (48.2240728, 17.3835125), (48.1788400, 17.1920305), 17.6),
    ("BA-SC-D1", "Bratislava-D1 → Senec", "D1",
     (48.1787464, 17.1921416), (48.2240728, 17.3835125), 16.8),
    ("SA-BA-R7", "Šamorín → Bratislava-Nivy", "R7",
     (48.0298858, 17.3098596), (48.1337600, 17.1585672), 18.0),
    ("BA-SA-R7", "Bratislava-Nivy → Šamorín", "R7",
     (48.1339966, 17.1576793), (48.0298858, 17.3098596), 17.6),
]

MAX_LENGTH_CHANGE = 0.05
DELAY_MIN = 5.0
DELAY_PERCENT = 0.30
LEGACY_DELAY_MIN = 10.0  # comparator only; no longer current threshold


def as_coords(p):
    return f"{p[0]:.7f},{p[1]:.7f}"


def contains_road(names, road):
    pattern = re.compile(r"(?<![A-Z0-9])" + re.escape(road.upper()) + r"(?![A-Z0-9])")
    return any(pattern.search(str(n).upper()) for n in names)


def road_guard(expected, names):
    """Coarse corridor classification, NOT verified route geometry."""
    if expected == "D2":
        required, forbidden = ("D2", "D4"), ()
    elif expected == "502":
        required, forbidden = ("502",), ("D1", "D4")
    elif expected == "D1":
        required, forbidden = ("D1",), ("61", "D4")
    else:  # R7
        required, forbidden = ("R7", "63"), ("503", "D4")
    missing = [r for r in required if not contains_road(names, r)]
    detours = [r for r in forbidden if contains_road(names, r)]
    if expected == "R7" and any("Šamorín-sever" in str(n) for n in names):
        detours.append("Šamorín-sever")
    return not missing and not detours, missing, detours


def compute_metrics(raw):
    segments = raw.get("results", raw.get("result", []))
    if not isinstance(segments, list) or not segments:
        raise ValueError("No segments")
    # Distinguish current estimates from provider's non-live and free-flow estimates.
    keys = ("crossTime", "crossTimeWithoutRealTime", "crossTimeFreeFlow", "length")
    if any(not isinstance(s, dict) or
           any(not isinstance(s.get(k), (int, float)) or
               not math.isfinite(s[k]) or s[k] < 0 for k in keys)
           for s in segments):
        raise ValueError("Incomplete travel-time reference: no alert calculation")
    seconds = sum(s["crossTime"] for s in segments)
    non_live = sum(s["crossTimeWithoutRealTime"] for s in segments)
    free_flow = sum(s["crossTimeFreeFlow"] for s in segments)
    km = sum(s["length"] for s in segments) / 1000
    if seconds <= 0 or non_live <= 0 or km <= 0:
        raise ValueError("Invalid route time/length")
    return {
        "minutes": round(seconds / 60, 1),
        "non_live_minutes": round(non_live / 60, 1),
        "free_flow_minutes": round(free_flow / 60, 1),
        "km": round(km, 2),
        "delta_min": round((seconds - non_live) / 60, 1),
        "delta_pct": round((seconds / non_live - 1) * 100, 1),
        "threshold_candidate": (
            (seconds - non_live) / 60 >= DELAY_MIN
            and seconds / non_live - 1 >= DELAY_PERCENT
        ),
        "legacy_10min_candidate": (
            (seconds - non_live) / 60 >= LEGACY_DELAY_MIN
            and seconds / non_live - 1 >= DELAY_PERCENT
        ),
    }


def examine(route, raw):
    route_id, desc, corridor, start, end, expected_km = route
    names = [str(x) for x in (raw.get("streetNames") or []) if x]
    ok, missing, detours = road_guard(corridor, names)
    if not ok:
        return "REJECT_CORRIDOR", {"missing": missing, "detours": detours}
    try:
        metrics = compute_metrics(raw)
    except (ValueError, TypeError, KeyError) as error:
        return "REJECT_BAD_DATA", {"reason": str(error)}
    drift_pct = abs(metrics["km"] / expected_km - 1)
    if drift_pct > MAX_LENGTH_CHANGE:
        return "REVIEW_ROUTE_LENGTH", {
            "km": metrics["km"], "expected_km": expected_km,
            "change_pct": round(drift_pct * 100, 1),
        }
    return "CANDIDATE_ENDPOINT_ONLY", metrics


async def main():
    print("INFO DOPRAV – TWO-POINT ROUTE PILOT")
    print("TEST_ONLY=true PUBLIC_PUBLISHING=false RECURRING=false")
    print("timestamp=" + datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("Current approved threshold: +5 min and +30%; old +10 min shown for comparison.")
    print("Both are single-reading candidates only. No alerts without second consecutive sample.")
    print("Not an accident detector. Road-name guard cannot prove exact geometry.")
    count = 0
    async with WazeRouteCalculator(region="EU") as waze:
        for route in ENDPOINTS:
            route_id, desc, corridor, start, end, expected_km = route
            print(f"\\n=== {route_id} | {desc} | {corridor} ===")
            try:
                raw_routes = await waze.get_routes(
                    waze.coords_string_parser(as_coords(start)),
                    waze.coords_string_parser(as_coords(end)),
                    alternatives=2,
                )
                best = None
                for alt_idx, raw in enumerate(raw_routes or [], 1):
                    status, details = examine(route, raw)
                    print(f" ALT={alt_idx} STATUS={status} DATA={details}")
                    if status == "CANDIDATE_ENDPOINT_ONLY" and best is None:
                        best = (alt_idx, details)
                if best:
                    count += 1
                    print(f" SELECTED_ALT={best[0]} READABLE=true PUBLISHING=false")
                    print(f" POLICY_5MIN_CANDIDATE={best[1]['threshold_candidate']} "
                          f"OLD_10MIN_CANDIDATE={best[1]['legacy_10min_candidate']} "
                          f"CONFIRMED=false")
                else:
                    print(" NO_COMPARABLE_ROUTE: NO ALERT")
            except Exception as e:
                print(f" ERROR={type(e).__name__}: {str(e)[:150]}")
    print(f"\\nSUMMARY candidates={count}/8 confirmed_alerts=0 published=0")
    if count == 0:
        raise RuntimeError("No valid endpoint data")


if __name__ == "__main__":
    asyncio.run(main())
