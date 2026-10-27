"""Inspect raw Waze route segment geometry against the existing eight-direction registry.

Manual diagnostics only. No scheduled trigger, external publishing, storage, or secrets.
The Waze 'path' sample may be sparse: proximity is indicative, NOT definitive
proof of continuous corridor compliance or the correct motorway carriageway.
Reference points: Info_doprav_register_tras.md (26 Oct 2026), OSM contributors.
"""
import asyncio
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from pywaze.route_calculator import WazeRouteCalculator

from test_eight_routes import ROUTES, point


def haversine_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    q = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 12742000 * math.asin(min(1, math.sqrt(q)))


def decode_path(data):
    """Collect explicit WGS84 x/y pairs without guessing undocumented geometry formats."""
    if not isinstance(data, dict):
        return None
    try:
        x, y = float(data["x"]), float(data["y"])
        if 16 < x < 18 and 47 < y < 49:
            return (y, x)
    except (KeyError, TypeError, ValueError):
        pass
    return None


def summarize_alternative(raw, route, idx):
    segments = raw.get("results", raw.get("result", []))
    name = raw.get("routeName", "UNNAMED")
    if not isinstance(segments, list):
        print(f"  ALT={idx} invalid segments; status=UNVERIFIED")
        return

    points = [coords for seg in segments if isinstance(seg, dict)
              if (coords := decode_path(seg.get("path"))) is not None]
    names = [str(s) for s in (raw.get("streetNames") or []) if s]
    route_id, title, required, start, end, checkpoints = route

    approx_min_dist = []
    nearest_indices = []
    for cp in checkpoints:
        if points:
            dists = [haversine_m(cp, p) for p in points]
            nearest = min(range(len(dists)), key=lambda i: dists[i])
            nearest_indices.append(nearest)
            approx_min_dist.append(round(dists[nearest]))
        else:
            nearest_indices.append(None)
            approx_min_dist.append(None)

    ordered = (all(
        a is not None and b is not None and a <= b
        for a, b in zip(nearest_indices, nearest_indices[1:])
    ) if len(nearest_indices) > 1 else None)
    # Minimum path-point distances are coarse; NEVER promote to VERIFIED.
    core_label = required.casefold() in name.casefold()
    print(f"  ALT={idx} name={name!r} segments={len(segments)} path_points={len(points)} "
          f"label_plausible={core_label} checkpoint_order_plausible={ordered} STATUS=UNVERIFIED")
    print(f"  checkpoint_distances_to_nearest_sample_m={approx_min_dist}")
    print(f"  checkpoint_nearest_sample_indices={nearest_indices}")
    print(f"  road_names={names}")
    if segments:
        print(f"  first_segment_keys={sorted(str(k) for k in segments[0])}")
        sample_path = segments[0].get("path")
        if isinstance(sample_path, dict):
            print(f"  path_fields={sorted(str(k) for k in sample_path.keys())}")
        else:
            print(f"  path_type={type(sample_path).__name__}")
    if points:
        max_gap = max((haversine_m(a, b) for a, b in zip(points, points[1:])), default=0)
        print(f"  max_straight_distance_between_samples_m={round(max_gap)}")
    print("  Note: sample distances do not verify full road geometry, exits or lane direction.")


async def main():
    print("INFO DOPRAV – RAW GEOMETRY DIAGNOSTIC", flush=True)
    print("timestamp=" + datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true ROUTE_VERIFICATION=false PUBLIC_PUBLISHING=false")
    completed = 0
    async with WazeRouteCalculator(region="EU") as client:
        for route in ROUTES:
            route_id, title, required, start, end, checkpoints = route
            print(f"\n=== {route_id}: {title}; expected={required} ===", flush=True)
            try:
                raw_routes = await client.get_routes(
                    client.coords_string_parser(point(start)),
                    client.coords_string_parser(point(end)),
                    alternatives=2,
                )
                if not raw_routes:
                    print("NO_ROUTES; status=UNVERIFIED", flush=True)
                    continue
                completed += 1
                for i, alt in enumerate(raw_routes, 1):
                    summarize_alternative(alt, route, i)
            except Exception as ex:
                print(f"ERROR={type(ex).__name__}: {str(ex)[:160]}", flush=True)
    print(f"\nDIAGNOSTIC_COMPLETED={completed}/8, VERIFIED_CORRIDORS=0")
    if completed == 0:
        raise RuntimeError("No raw route responses")


if __name__ == "__main__":
    asyncio.run(main())
