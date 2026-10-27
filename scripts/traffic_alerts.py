"""Info doprav: pure candidate traffic alert confirmation logic.

This module has NO provider calls, secrets, networking, storage or Telegram.
Only compares records supplied to it. Production integration must persist the
last comparable observation and deduplicate events before any public message.
Times must be timezone-aware and correspond to the end of provider collection.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

DELAY_SECONDS = 5 * 60
MINIMUM_RATIO = 0.30
MIN_SEPARATION = timedelta(minutes=5)
MAX_SEPARATION = timedelta(minutes=30)


@dataclass(frozen=True)
class Observation:
    route_id: str
    observed_at: datetime
    travel_seconds: float
    reference_seconds: float
    route_family: tuple[str, ...]
    road_fingerprint: str
    comparable_candidate: bool


def is_single_candidate(obs: Observation) -> bool:
    if not obs.comparable_candidate:
        return False
    if obs.observed_at.tzinfo is None or obs.observed_at.utcoffset() is None:
        return False
    if obs.reference_seconds <= 0 or obs.travel_seconds <= 0:
        return False
    delay = obs.travel_seconds - obs.reference_seconds
    return delay >= DELAY_SECONDS and delay / obs.reference_seconds >= MINIMUM_RATIO


def confirm_two(previous: Observation | None, current: Observation) -> str:
    """One of READY_FOR_PRIVATE_REVIEW, NEW_SINGLE_CANDIDATE, or BLOCK_*.

    Caller never publishes automatically. If a route changes, reset previous.
    """
    if not is_single_candidate(current):
        return "BLOCK_CURRENT_BELOW_THRESHOLD_OR_INVALID"
    if previous is None:
        return "NEW_SINGLE_CANDIDATE"
    if not is_single_candidate(previous):
        return "NEW_SINGLE_CANDIDATE"
    if current.route_id != previous.route_id:
        return "BLOCK_DIFFERENT_ROUTE"
    if (current.route_family != previous.route_family or
        current.road_fingerprint != previous.road_fingerprint):
        return "BLOCK_ROUTE_CHANGED"
    interval = current.observed_at - previous.observed_at
    if not MIN_SEPARATION <= interval <= MAX_SEPARATION:
        return "BLOCK_SAMPLE_INTERVAL"
    return "READY_FOR_PRIVATE_REVIEW"
