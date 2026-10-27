"""No-network regression tests of threshold and two comparable measurements."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from traffic_alerts import Observation, confirm_two, is_single_candidate

ZONE=ZoneInfo("Europe/Bratislava")


def observation(hour, minute, travel, reference, *,
                family=("PRAZSKA",), route_id="BA-D2-LAMAC-CENTRUM",
                fingerprint="06a5dfc82c5c", comparable=True):
    return Observation(
        route_id=route_id,
        observed_at=datetime(2026,10,27,hour,minute,tzinfo=ZONE),
        travel_seconds=travel*60, reference_seconds=reference*60,
        route_family=family, road_fingerprint=fingerprint,
        comparable_candidate=comparable,
    )


class TrafficConfirmationTests(unittest.TestCase):
    def test_lamac_0948_and_1000_only_private_candidate(self):
        first=observation(9,48,16.7,9.3)
        second=observation(10,0,16.4,9.2)
        self.assertTrue(is_single_candidate(first))
        self.assertTrue(is_single_candidate(second))
        self.assertEqual(confirm_two(first,second),"READY_FOR_PRIVATE_REVIEW")

    def test_first_sample_is_insufficient(self):
        self.assertEqual(confirm_two(None,observation(9,48,16.7,9.3)),
                         "NEW_SINGLE_CANDIDATE")

    def test_change_of_road_family_blocks(self):
        self.assertEqual(confirm_two(
            observation(9,48,16.7,9.3),
            observation(10,0,16.4,9.2,family=("MOST_SNP",))),
            "BLOCK_ROUTE_CHANGED")

    def test_change_of_signature_blocks(self):
        self.assertEqual(confirm_two(
            observation(9,48,16.7,9.3),
            observation(10,0,16.4,9.2,fingerprint="DIFFERENT")),
            "BLOCK_ROUTE_CHANGED")

    def test_different_route_blocks(self):
        self.assertEqual(confirm_two(
            observation(9,48,16.7,9.3),
            observation(10,0,16.4,9.2,route_id="OTHER")),
            "BLOCK_DIFFERENT_ROUTE")

    def test_long_interval_blocks(self):
        self.assertEqual(confirm_two(
            observation(9,10,16.7,9.3),
            observation(10,0,16.4,9.2)),
            "BLOCK_SAMPLE_INTERVAL")

    def test_under_threshold_blocks(self):
        self.assertEqual(confirm_two(
            observation(9,48,16.7,9.3),
            observation(10,0,13.0,9.2)),
            "BLOCK_CURRENT_BELOW_THRESHOLD_OR_INVALID")

    def test_unverified_candidate_blocks(self):
        self.assertFalse(is_single_candidate(
            observation(9,48,16.7,9.3,comparable=False)))

    def test_absolute_and_relative_threshold(self):
        self.assertFalse(is_single_candidate(observation(9,48,14.0,9.3)))
        self.assertFalse(is_single_candidate(observation(9,48,25.0,20.1)))
        self.assertFalse(is_single_candidate(observation(9,48,26.0,20.1)))
        self.assertTrue(is_single_candidate(observation(9,48,27.0,20.0)))


if __name__=="__main__":
    unittest.main()
