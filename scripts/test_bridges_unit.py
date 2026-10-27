"""Offline unit tests for preliminary OSM-based bridge monitoring; NO HTTP."""
import unittest

from waze_bridges_discover import (
    BRIDGES, endpoint_options, expected_bridge_in_waze,
    road_bridge_way_tags, route_name_bridge, usable_candidates,
)


def way(name, points, *, osm_id=100, highway="primary", oneway="yes"):
    return {
        "type":"way","id":osm_id,
        "tags":{"highway":highway,"bridge":"yes","name":name,"oneway":oneway},
        "geometry":[{"lat":lat,"lon":lon} for lat,lon in points]
    }


class BridgeTests(unittest.TestCase):
    def test_three_explicit_bridge_names(self):
        self.assertEqual(set(BRIDGES), {"SNP","APOLLO","PRISTAVNY"})

    def test_bridge_names_and_accents(self):
        self.assertEqual(route_name_bridge(way("Most SNP",[])), "SNP")
        self.assertEqual(route_name_bridge(way("Most Apollo",[])), "APOLLO")
        self.assertEqual(route_name_bridge(way("Prístavný most",[])), "PRISTAVNY")

    def test_non_motor_vehicle_ways_rejected(self):
        self.assertFalse(road_bridge_way_tags(way("Most Apollo", [], highway="footway")))
        item=way("Most Apollo",[],highway="primary")
        item["tags"]["motorcar"]="no"
        self.assertFalse(road_bridge_way_tags(item))

    def test_long_named_motor_bridge_candidates(self):
        features = [
            way("Most Apollo",[(48.142,17.13),(48.135,17.13)],osm_id=1),
            way("Most SNP",[(48.14,17.11),(48.13,17.11)],osm_id=2),
            way("Some unrelated bridge",[(48.14,17.12),(48.13,17.12)],osm_id=3),
        ]
        result=usable_candidates(features)
        self.assertEqual(len(result["SNP"]),1)
        self.assertEqual(len(result["APOLLO"]),1)
        self.assertEqual(len(result["PRISTAVNY"]),0)

    def test_oneway_does_not_assume_reverse_direction(self):
        candidates = usable_candidates([
            way("Most SNP",[(48.14,17.11),(48.135,17.11)],oneway="yes")
        ])
        options=endpoint_options(candidates["SNP"])
        self.assertIn("N_TO_S", options)
        self.assertNotIn("S_TO_N",options)

    def test_bidirectional_road_has_reverse_candidate(self):
        candidates=usable_candidates([
            way("Most Apollo",[(48.14,17.11),(48.135,17.11)],oneway="no")
        ])
        options=endpoint_options(candidates["APOLLO"])
        self.assertEqual(set(options),{"N_TO_S","S_TO_N"})

    def test_waze_label_required_for_matching(self):
        self.assertTrue(expected_bridge_in_waze("SNP","Most SNP",["Staromestská"]))
        self.assertTrue(expected_bridge_in_waze("PRISTAVNY","D1",["Prístavný most"]))
        self.assertFalse(expected_bridge_in_waze("APOLLO","D1",["Prístavný most"]))


if __name__=="__main__":
    unittest.main()
