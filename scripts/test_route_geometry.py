"""Diagnose Waze's route geometry for eight registered Info doprav directions.

Manual-only diagnostic. Never publishes traffic, modifies Sheets, saves raw
responses, or claims to have validated the exact motorway carriageway.

The Waze 'path' field contains sparse route segment sample points, NOT a
continuous street-level polyline. A projection onto a long chord is ambiguous.
Reference: Info_doprav_register_tras.md, 26 Oct 2026, © OSM contributors.
"""
import asyncio
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from pywaze.route_calculator import WazeRouteCalculator
from test_eight_routes import ROUTES, point


MAX_NEAR_M = 50
MAX_SHORT_CHORD_M = 450


def decode_path(data):
    if not isinstance(data, dict):
        return None
    try:
        lon, lat = float(data["x"]), float(data["y"])
        if 16 < lon < 18 and 47 < lat < 49:
            return (lat, lon)
    except (KeyError, TypeError, ValueError):
        pass
    return None


def checkpoint_segment(cp, a, b):
    """Distance from point to a finite straight chord, locally projected in m.

    Do not treat this as true road geometry for long Waze segments.
    """
    m_lat = 111195.0
    m_lon = m_lat * math.cos(math.radians(cp[0]))
    ax = (a[1] - cp[1]) * m_lon
    ay = (a[0] - cp[0]) * m_lat
    bx = (b[1] - cp[1]) * m_lon
    by = (b[0] - cp[0]) * m_lat
    dx, dy = bx - ax, by - ay
    squared = dx * dx + dy * dy
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / squared)) if squared else 0.0
    return math.hypot(ax + t * dx, ay + t * dy), math.sqrt(squared), t


def checkpoint_diagnostic(cp, points):
    if len(points) < 2:
        return {"state": "INSUFFICIENT_POINTS", "dist_m": None,
                "chord_m": None, "at": None}
    candidates = [(*checkpoint_segment(cp, points[i], points[i + 1]), i)
                  for i in range(len(points) - 1)]
    # (distance, length of connecting chord, interpolation fraction, chord index)
    nearest = min(candidates, key=lambda p: p[0])
    short_close = [c for c in candidates
                   if c[0] <= MAX_NEAR_M and c[1] <= MAX_SHORT_CHORD_M]
    if short_close:
        selected = min(short_close, key=lambda p: p[0])
        state = "NEAR_SHORT_CHORD"
    else:
        selected = nearest
        state = ("NEAR_SPARSE_CHORD_ONLY" if nearest[0] <= MAX_NEAR_M
                 else "NO_CLOSE_SAMPLE_GEOMETRY")
    d, gap, frac, idx = selected
    return {"state": state, "dist_m": round(d), "chord_m": round(gap),
            "at": round(idx + frac, 2)}


def road_token(names, token):
    # Match a complete road label; no confusion between 61 and 161.
    return any(re.search(r"(?<![A-Z0-9])" + re.escape(token.upper())
                         + r"(?![A-Z0-9])", text.upper())
               for text in names)


def classify_road_names(route_id, names):
    if route_id.startswith(("ST-", "BA-ST")):
        missing = [x for x in ("D2", "D4") if not road_token(names, x)]
        forbidden = ["Bory"] if any("Bory" in x for x in names) else []
    elif "-PK-" in route_id or route_id.startswith("PK-"):
        missing = ["502"] if not road_token(names, "502") else []
        forbidden = [x for x in ("D1", "D4") if road_token(names, x)]
    elif "-SC-" in route_id or route_id.startswith("SC-"):
        missing = ["D1"] if not road_token(names, "D1") else []
        forbidden = [x for x in ("61", "D4") if road_token(names, x)]
    else:
        missing = ["R7"] if not road_token(names, "R7") else []
        forbidden = [x for x in ("503", "D4") if road_token(names, x)]
        if any("Šamorín-sever" in x for x in names):
            forbidden.append("Šamorín-sever")
    if forbidden:
        return "REJECT_ALTERNATIVE", f"forbidden={forbidden}"
    if missing:
        return "REVIEW_MISSING_REQUIRED_ROAD", f"missing={missing}"
    return "CANDIDATE_UNVERIFIED", "route_labels_plausible_only"


def summarize(raw, route, index):
    route_id, title, required, start, end, checkpoints = route
    segments = raw.get("results", raw.get("result", []))
    if not isinstance(segments, list):
        print(f"  ALT={index} BAD_SEGMENT_FORMAT; STATUS=UNVERIFIED")
        return
    path = [xy for s in segments if isinstance(s, dict)
            if (xy := decode_path(s.get("path"))) is not None]
    names = [str(s) for s in raw.get("streetNames", []) if s]
    label_state, label_reason = classify_road_names(route_id, names)
    print(f"  ALT={index} route_name={raw.get('routeName', '')!r}"
          f" segments={len(segments)} path_sample_points={len(path)}")
    print(f"  ROAD_LABEL_CHECK={label_state}; {label_reason}")
    diagnostic = [checkpoint_diagnostic(cp, path) for cp in checkpoints]
    for i, item in enumerate(diagnostic, 1):
        print(f"  checkpoint_{i} {item}")
    confident = [x for x in diagnostic if x["state"] == "NEAR_SHORT_CHORD"]
    ordered = (len(confident) == len(diagnostic)
               and all(a["at"] <= b["at"] for a, b in zip(diagnostic, diagnostic[1:])))
    print(f"  SAMPLE_POINT_ORDER_SUPPORT={ordered};"
          f" local_checkpoint_support={len(confident)}/{len(checkpoints)}")
    if len(path) > 1:
        gaps = [checkpoint_segment(a, a, b)[1] for a, b in zip(path, path[1:])]
        print(f"  largest_sample_gap_m={round(max(gaps))}"
              f" sparse_chords_over_{MAX_SHORT_CHORD_M}m="
              f"{sum(g > MAX_SHORT_CHORD_M for g in gaps)}")
    print("  FINAL=REJECT_ALTERNATIVE" if label_state == "REJECT_ALTERNATIVE"
          else "  FINAL=UNVERIFIED_REQUIRES_FULL_GEOMETRY_AND_MANUAL_REVIEW")


async def main():
    print("INFO DOPRAV – ROUTE GEOMETRY DIAGNOSTIC v2", flush=True)
    print("timestamp=" + datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true PUBLIC_PUBLISHING=false VERIFIED_CORRIDORS=0")
    print(f"Proximity requires <= {MAX_NEAR_M}m and chord length <= {MAX_SHORT_CHORD_M}m.")
    print("A long straight chord is not proof of a Waze road passing a point.")
    received = 0
    async with WazeRouteCalculator(region="EU") as waze:
        for route in ROUTES:
            route_id, title, required, start, end, checkpoints = route
            print(f"\n=== {route_id}: {title} (expected {required}) ===", flush=True)
            try:
                raw_routes = await waze.get_routes(
                    waze.coords_string_parser(point(start)),
                    waze.coords_string_parser(point(end)),
                    alternatives=2,
                )
                if not raw_routes:
                    print("NO_ROUTES", flush=True)
                    continue
                received += 1
                for idx, raw in enumerate(raw_routes, 1):
                    summarize(raw, route, idx)
            except Exception as e:
                print(f"ERROR={type(e).__name__}: {str(e)[:160]}", flush=True)
    print(f"\nSUMMARY directions_with_response={received}/8 VERIFIED_CORRIDORS=0")
    if not received:
        raise RuntimeError("No route data available")


if __name__ == "__main__":
    asyncio.run(main())
