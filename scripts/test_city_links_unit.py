"""Offline checks for city centre-route pairing; NO network requests."""
import unittest

from waze_city_links_pilot import city_links, CENTRE, AREA_CODES
from waze_endpoint_pilot import ENDPOINTS


class CityLinkTests(unittest.TestCase):
    def test_eight_links(self):
        links=city_links()
        self.assertEqual(len(links),8)
        self.assertEqual(len(set(x[0] for x in links)),8)

    def test_boundary_points_taken_from_original_registry(self):
        links=city_links()
        for idx in range(4):
            to_centre=links[2*idx]
            from_centre=links[2*idx+1]
            self.assertEqual(to_centre[2],ENDPOINTS[2*idx][4])
            self.assertEqual(from_centre[3],ENDPOINTS[2*idx+1][3])
            self.assertEqual(to_centre[3],CENTRE)
            self.assertEqual(from_centre[2],CENTRE)

    def test_centre_is_not_an_urban_profile_on_motorway(self):
        self.assertNotIn(CENTRE,[r[3] for r in ENDPOINTS])
        self.assertNotIn(CENTRE,[r[4] for r in ENDPOINTS])

    def test_four_unique_city_entry_points(self):
        self.assertEqual(len(AREA_CODES),4)
        self.assertEqual(len(set(r[2] for r in city_links()[::2])),4)


if __name__ == "__main__":
    unittest.main()
