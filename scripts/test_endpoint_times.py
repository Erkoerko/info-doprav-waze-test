"""Manual endpoint-only Waze traffic test for the eight registered directions.

Uses only start and end positions. Does not verify full corridor geometry,
store results, schedule measurements, or publish Telegram posts. Candidate
route road labels are a heuristic and can miss diversions.
"""
import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pywaze.route_calculator import WazeRouteCalculator
from test_eight_routes import ROUTES, point

def token_in_names(names, label):
    pat = re.compile(r"(?<![A-Z0-9])" + re.escape(label.upper()) + r"(?![A-Z0-9])")
    return any(pat.search(str(n).upper()) for n in names)

def candidate_check(route_id, route_name, roads):
    # Defensive, intentionally conservative; names are not geometry.
    names = [route_name] + list(roads)
    if route_id.endswith("-D2"):
        return token_in_names(names,"D2") and token_in_names(names,"D4") and not any("Bory" in str(x) for x in names)
    if route_id.endswith("-502"):
        return token_in_names(names,"502") and not (token_in_names(names,"D1") or token_in_names(names,"D4"))
    if route_id.endswith("-D1"):
        return token_in_names(names,"D1") and not (token_in_names(names,"61") or token_in_names(names,"D4"))
    if route_id.endswith("-R7"):
        return (token_in_names(names,"R7") and not token_in_names(names,"503")
                and not token_in_names(names,"D4")
                and not any("Šamorín-sever" in str(x) for x in names))
    return False

def segment_value(seg, *keys):
    for key in keys:
        if key in seg and isinstance(seg[key], (int,float)):
            return float(seg[key])
    return None

def parse_time(raw):
    segments = raw.get("results",raw.get("result"))
    if not isinstance(segments,list) or not segments:
        return None
    curr=baseline=freeflow=length=0.0
    has_baseline=has_freeflow=True
    for s in segments:
        if not isinstance(s,dict):
            return None
        c=segment_value(s,"crossTime","cross_time")
        b=segment_value(s,"crossTimeWithoutRealTime","cross_time_without_real_time")
        f=segment_value(s,"crossTimeFreeFlow","cross_time_free_flow")
        l=segment_value(s,"length")
        if c is None or l is None:
            return None
        curr+=c
        length+=l
        if b is None: has_baseline=False
        else: baseline+=b
        if f is None: has_freeflow=False
        else: freeflow+=f
    return curr/60, baseline/60 if has_baseline else None, freeflow/60 if has_freeflow else None, length/1000

async def main():
    print("INFO DOPRAV WAZE – ENDPOINT-ONLY TRAFFIC TEST")
    print("TIME="+datetime.now(ZoneInfo("Europe/Bratislava")).isoformat(timespec="seconds"))
    print("TEST_ONLY=true SCHEDULED=false PUBLIC_PUBLISHING=false")
    print("Baseline 'without real time' is NOT automatically an hourly typical travel time.")
    count=0
    async with WazeRouteCalculator(region="EU") as waze:
        for route_id,title,required,start,end,_checkpoints in ROUTES:
            print(f"\n=== {route_id} | {title} | {point(start)} -> {point(end)} ===")
            try:
                alts=await waze.get_routes(
                    waze.coords_string_parser(point(start)),
                    waze.coords_string_parser(point(end)),
                    alternatives=2,
                )
                valid=[]
                for i,raw in enumerate(alts or [],1):
                    roads=[str(v) for v in raw.get("streetNames",[]) if v]
                    name=str(raw.get("routeName",""))
                    plausible=candidate_check(route_id,name,roads)
                    t=parse_time(raw)
                    if t is None:
                        print(f"ALT={i} INVALID_TIME; exclude")
                        continue
                    mins,typical,freeflow,km=t
                    print(f"ALT={i} name={name!r} min={mins:.1f} km={km:.1f} "
                          f"baseline_no_realtime={round(typical,1) if typical is not None else 'n/a'} "
                          f"freeflow={round(freeflow,1) if freeflow is not None else 'n/a'} "
                          f"label_candidate={plausible}")
                    if plausible:
                        valid.append((mins,typical,km,i))
                if not valid:
                    print("RESULT=NO_COMPARABLE_CANDIDATE")
                    continue
                mins,baseline,km,idx=min(valid,key=lambda v:v[0])
                count+=1
                if baseline is None or baseline<=0:
                    print(f"RESULT=UNVERIFIED_ALT_{idx}; delay cannot be calculated")
                else:
                    delay=mins-baseline
                    pct=100*delay/baseline
                    threshold=delay>=10 and pct>=30
                    print(f"RESULT=UNVERIFIED_ALT_{idx} duration={mins:.1f} "
                          f"baseline_without_real_time={baseline:.1f} "
                          f"delta_min={delay:+.1f} delta_pct={pct:+.0f}% "
                          f"threshold_candidate={threshold} "
                          f"ALERT=false (needs second measurement, baseline assessment and route validation)")
            except Exception as e:
                print(f"ERROR={type(e).__name__} {str(e)[:180]}")
    print(f"\nSUMMARY={count}/8 candidate route readings; VERIFIED_CORRIDORS=0; ALERTS_SENT=0")
    if count==0:
        raise RuntimeError("No candidate travel times returned")

if __name__=="__main__":
    asyncio.run(main())
