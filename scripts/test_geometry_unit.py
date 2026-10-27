"""Offline regression tests for Waze geometry diagnostics; makes no web calls."""
import unittest

from test_route_geometry import (
    checkpoint_diagnostic,
    checkpoint_segment,
    classify_road_names,
    road_token,
)


class GeometryDiagnosticTests(unittest.TestCase):
    def test_exact_point_on_short_segment(self):
        middle = (48.2000, 17.2000)
        pts = [(48.1995, 17.2000), (48.2005, 17.2000)]
        p = checkpoint_diagnostic(middle, pts)
        self.assertEqual(p["state"], "NEAR_SHORT_CHORD")
        self.assertLessEqual(p["dist_m"], 1)

    def test_near_long_chord_is_not_good_evidence(self):
        middle = (48.2000, 17.2000)
        pts = [(48.17, 17.2), (48.23, 17.2)]
        p = checkpoint_diagnostic(middle, pts)
        self.assertEqual(p["state"], "NEAR_SPARSE_CHORD_ONLY")
        self.assertGreater(p["chord_m"], 450)

    def test_away_from_sample(self):
        p = checkpoint_diagnostic((48.3, 17.3), [(48.2, 17.2), (48.2005, 17.2)])
        self.assertEqual(p["state"], "NO_CLOSE_SAMPLE_GEOMETRY")

    def test_no_points(self):
        self.assertEqual(checkpoint_diagnostic((48.2,17.2), [])["state"], "INSUFFICIENT_POINTS")

    def test_token_boundary(self):
        self.assertFalse(road_token(["161"], "61"))
        self.assertTrue(road_token(["exit D1 → Bratislava"], "D1"))

    def test_reject_senec_alternative(self):
        status, _ = classify_road_names("SC-BA-D1", ["D1", "61", "D4"])
        self.assertEqual(status, "REJECT_ALTERNATIVE")

    def test_reject_samorin_north(self):
        status, _ = classify_road_names("BA-SA-R7", ["R7", "exit Šamorín-sever", "503"])
        self.assertEqual(status, "REJECT_ALTERNATIVE")

    def test_samorin_west_can_remain_candidate(self):
        status, _ = classify_road_names("BA-SA-R7", ["R7", "exit 14 Šamorín-západ", "63"])
        self.assertEqual(status, "CANDIDATE_UNVERIFIED")

    def test_pezinok_main_road_can_remain_candidate(self):
        status, _ = classify_road_names("PK-BA-502", ["502", "Krajinská cesta"])
        self.assertEqual(status, "CANDIDATE_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
