"""No-network safety tests: classify city route alternatives conservatively."""
import unittest

from city_route_assessment import (
    normalize, travel_family, route_fingerprint,
    is_restricted, select_fastest, comparison_status,
)
from waze_endpoint_pilot import compute_metrics


def raw(roads, live_minutes, baseline_minutes, distance_km=7.6, restricted=False):
    return {
        "routeName": roads[0],
        "streetNames": roads,
        "minPassengers": 2 if restricted else 0,
        "results": [{
            "crossTime": live_minutes * 60,
            "crossTimeWithoutRealTime": baseline_minutes * 60,
            "crossTimeFreeFlow": max(1, baseline_minutes - 1) * 60,
            "length": distance_km * 1000,
        }]
    }


class CityAssessmentTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize("  PRÍSTAVNÝ MOST "), "pristavny most")

    def test_bridge_is_recognized_under_common_names(self):
        self.assertIn("MOST_SNP", travel_family(["Nový most"]))
        self.assertIn("MOST_SNP", travel_family(["Most Slovenského národného povstania"]))
        self.assertIn("MOST_LAFRANCONI", travel_family(["Most Lanfranconi"]))
        self.assertIn("PRISTAVNY_MOST", travel_family(["Prístavný most"]))

    def test_prazska_and_snp_are_different_families(self):
        a = travel_family(["Pražská", "Štefánikova"])
        b = travel_family(["Most SNP", "Einsteinova", "Most Lafranconi"])
        self.assertNotEqual(a, b)

    def test_fingerprint_same_for_whitespace_and_accents(self):
        self.assertEqual(route_fingerprint([" Prístavný   most "]),
                         route_fingerprint(["Pristavny most"]))
        self.assertNotEqual(route_fingerprint(["Pražská"]),
                            route_fingerprint(["Most SNP"]))

    def test_fastest_unrestricted_alternative_selected(self):
        routes = [
            raw(["Pražská"], 16.7, 9.3),
            raw(["Most SNP", "Most Lafranconi"], 10.0, 9.3, 12.4),
            raw(["Most SNP"], 7.0, 6.0, 12.4, restricted=True),
        ]
        selected = select_fastest(routes, compute_metrics)
        self.assertEqual(selected[0], 2)
        self.assertFalse(selected[2]["threshold_candidate"])

    def test_lamac_inbound_qualifies_single_measurement_only(self):
        selected = select_fastest(
            [raw(["Pražská"], 16.7, 9.3)], compute_metrics)
        self.assertTrue(selected[2]["threshold_candidate"])
        self.assertAlmostEqual(selected[2]["delta_min"], 7.4)
        self.assertEqual(comparison_status(None, None, selected), "FIRST_SAMPLE")

    def test_family_change_blocks_comparison(self):
        first = select_fastest([raw(["Pražská"], 16.7, 9.3)], compute_metrics)
        second = select_fastest([raw(["Most SNP"], 16.0, 9.3)], compute_metrics)
        self.assertEqual(comparison_status(first[3], first[4], second),
                         "ROUTE_FAMILY_CHANGED")

    def test_same_fingerprint_is_not_geometry_verification(self):
        x = select_fastest([raw(["Pražská"], 16, 9)], compute_metrics)
        self.assertEqual(comparison_status(x[3], x[4], x),
                         "ROAD_LABELS_STABLE_NOT_GEOMETRY_VERIFIED")

    def test_invalid_and_missing_route_is_excluded(self):
        invalid = {"routeName": "Pražská", "streetNames": ["Pražská"], "results": []}
        self.assertIsNone(select_fastest([invalid], compute_metrics))
        self.assertEqual(comparison_status(None, None, None), "NO_ROUTE")


if __name__ == "__main__":
    unittest.main()
