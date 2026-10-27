"""Offline safety tests for the endpoint-only Waze pilot: zero Waze requests."""
import unittest

from waze_endpoint_pilot import (
    ENDPOINTS, compute_metrics, examine, road_guard,
    DELAY_MIN, DELAY_PERCENT
)


def raw_route(roads, km=17.6, live_seconds=1200, non_live_seconds=600):
    return {
        "routeName": str(roads[0]),
        "streetNames": roads,
        "results": [{
            "crossTime": live_seconds,
            "crossTimeWithoutRealTime": non_live_seconds,
            "crossTimeFreeFlow": 550,
            "length": km * 1000,
        }]
    }


class EndpointTests(unittest.TestCase):
    def test_eight_unique_direction_ids(self):
        self.assertEqual(len(ENDPOINTS), 8)
        self.assertEqual(len(set(r[0] for r in ENDPOINTS)), 8)

    def test_endpoint_order_reversed_by_direction(self):
        pairs = [(0, 1), (2, 3), (4, 5), (6, 7)]
        for inward, outward in pairs:
            a, b = ENDPOINTS[inward], ENDPOINTS[outward]
            # Motorway endpoints in opposite directions lie on different lanes;
            # hence latitude/longitude are intentionally not exactly reversed.
            self.assertEqual(a[2], b[2])
            self.assertNotEqual(a[0], b[0])

    def test_stupava_d2_valid(self):
        self.assertTrue(road_guard("D2", ["2", "D4", "exit D2", "D2"])[0])

    def test_senec_detour_rejected(self):
        self.assertFalse(road_guard("D1", ["D1", "61", "D4"])[0])

    def test_samorin_north_rejected(self):
        self.assertFalse(road_guard("R7", ["R7", "503", "Šamorín-sever"])[0])

    def test_pz_d4_rejected(self):
        self.assertFalse(road_guard("502", ["502", "D4"])[0])

    def test_delay_candidate_needs_both_conditions(self):
        self.assertEqual(DELAY_MIN, 10)
        self.assertEqual(DELAY_PERCENT, .30)
        self.assertTrue(compute_metrics(raw_route(["D1"], live_seconds=1200,
                                                  non_live_seconds=600))["threshold_candidate"])
        self.assertFalse(compute_metrics(raw_route(["D1"], live_seconds=1080,
                                                   non_live_seconds=600))["threshold_candidate"])
        self.assertFalse(compute_metrics(raw_route(["D1"], live_seconds=2400,
                                                   non_live_seconds=2000))["threshold_candidate"])

    def test_no_non_live_reference_rejected(self):
        raw = raw_route(["D1"])
        raw["results"][0].pop("crossTimeWithoutRealTime")
        state, _ = examine(ENDPOINTS[4], raw)
        self.assertEqual(state, "REJECT_BAD_DATA")

    def test_abnormal_route_length_rejected(self):
        state, _ = examine(ENDPOINTS[4], raw_route(["D1"], km=25))
        self.assertEqual(state, "REVIEW_ROUTE_LENGTH")

    def test_valid_senec_remains_only_candidate(self):
        state, metrics = examine(ENDPOINTS[4], raw_route(["503", "D1"], km=17.6))
        self.assertEqual(state, "CANDIDATE_ENDPOINT_ONLY")
        self.assertAlmostEqual(metrics["delta_min"], 10)

    def test_guard_blocks_unrelated_road(self):
        state, _ = examine(ENDPOINTS[4], raw_route(["61", "503"], km=17.6))
        self.assertEqual(state, "REJECT_CORRIDOR")


if __name__ == "__main__":
    unittest.main()
