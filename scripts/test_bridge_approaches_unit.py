"""Offline tests for provisional approach candidate selection; no network calls."""
import unittest

from waze_bridge_approaches_pilot import (
    DECK, choose_node, bridge_in_names, is_car_road, matching_name,
    MAX_ENDPOINT_ROAD_KM, way_direction_alignment, approach_directness,
)


def road(osm_id, road_name, points, vehicle="yes"):
    return {"type":"way","id":osm_id,
            "tags":{"highway":"primary","name":road_name,"motorcar":vehicle},
            "geometry":[{"lat":lat,"lon":lon} for lat,lon in points]}


class BridgeApproachTests(unittest.TestCase):
    def test_exactly_six_directional_bridge_profiles(self):
        self.assertEqual(set(DECK),{"SNP","APOLLO","PRISTAVNY"})
        self.assertEqual(sum(len(x) for x in DECK.values()),6)

    def test_outward_candidate_selection_from_real_way_geometry(self):
        start=(48.1400,17.1000)
        end=(48.1350,17.1000)
        ways=[
            road(1,"Staromestská",[(48.1500,17.1000)]),
            road(2,"Panónska cesta",[(48.1250,17.1000)]),
        ]
        before=choose_node(ways,start,end,"BEFORE",("staromestska",))
        after=choose_node(ways,start,end,"AFTER",("panonska",))
        self.assertEqual(before["osm_way_id"],1)
        self.assertEqual(after["osm_way_id"],2)
        self.assertGreater(before["coord"][0],start[0])
        self.assertLess(after["coord"][0],end[0])

    def test_wrong_road_returns_none(self):
        self.assertIsNone(
            choose_node([road(1,"Panónska",[(48.1500,17.1000)])],
                        (48.1400,17.1000),(48.1350,17.1000),
                        "BEFORE",("staromestska",)))

    def test_near_bridge_not_valid_approach(self):
        self.assertIsNone(
            choose_node([road(1,"Staromestská",[(48.1410,17.1000)])],
                        (48.1400,17.1000),(48.1350,17.1000),
                        "BEFORE",("staromestska",)))

    def test_vehicle_restrictions(self):
        self.assertFalse(is_car_road({"highway":"primary","motorcar":"no"}))
        self.assertFalse(is_car_road({"highway":"footway"}))
        self.assertTrue(is_car_road({"highway":"motorway","ref":"D1"}))

    def test_d1_by_ref(self):
        self.assertTrue(matching_name({"highway":"motorway","ref":"D1"},("d1",)))
        self.assertFalse(matching_name({"name":"Staromestská"},("d1",)))

    def test_bridge_name_diagnostics(self):
        self.assertEqual(bridge_in_names("SNP",{"streetNames":["Most SNP"]}),(True,False))
        self.assertEqual(bridge_in_names("APOLLO",{"streetNames":["Prístavný most"]}),(False,True))
        self.assertEqual(bridge_in_names("SNP",{"streetNames":["Most SNP","Prístavný most"]}),(True,True))

    def test_d1_oneway_filter_avoids_opposite_carriageway(self):
        # South of Pristavny, both D1 carriageways are adjacent.
        # The historical 13.46 km loop came from a wrong-side destination.
        deck_start=(48.1368599,17.1426615)
        deck_end=(48.1324385,17.1365996)
        wrong={
            "type":"way", "id":901,
            "tags":{"highway":"motorway","ref":"D1","oneway":"yes"},
            "geometry":[{"lat":48.1305,"lon":17.1260},
                        {"lat":48.1312,"lon":17.1275}]
        }
        correct={
            "type":"way", "id":902,
            "tags":{"highway":"motorway","ref":"D1","oneway":"yes"},
            "geometry":[{"lat":48.1312,"lon":17.1275},
                        {"lat":48.1305,"lon":17.1260}]
        }
        self.assertLess(way_direction_alignment(wrong,0,deck_start,deck_end),0)
        self.assertGreater(way_direction_alignment(correct,0,deck_start,deck_end),0)
        selected=choose_node([wrong,correct],deck_start,deck_end,
                             "AFTER",("d1",),strict_direction=True)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["osm_way_id"],902)
        self.assertGreaterEqual(selected["oneway_alignment"],0.30)

    def test_wrong_side_only_fails_closed(self):
        start=(48.1368599,17.1426615)
        end=(48.1324385,17.1365996)
        wrong={"type":"way","id":901,
               "tags":{"highway":"motorway","ref":"D1","oneway":"yes"},
               "geometry":[{"lat":48.1305,"lon":17.1260},
                           {"lat":48.1312,"lon":17.1275}]}
        self.assertIsNone(choose_node([wrong],start,end,"AFTER",("d1",),
                                      strict_direction=True))

    def test_observed_pristavny_13km_loop_is_rejected(self):
        north=(48.1420175,17.1552671)
        south=(48.1308479,17.126708)
        ok,straight_km,ratio=approach_directness(north,south,13.46)
        self.assertFalse(ok)
        self.assertGreater(ratio,2.2)
        self.assertGreater(13.46-straight_km,2.2)

    def test_observed_pristavny_27km_south_to_north_is_plausible(self):
        south=(48.1308479,17.126708)
        north=(48.1419151,17.1566405)
        ok,straight_km,ratio=approach_directness(south,north,2.70)
        self.assertTrue(ok)
        self.assertGreater(straight_km,2)

    def test_upper_length_guard(self):
        self.assertLessEqual(MAX_ENDPOINT_ROAD_KM,9.0)


if __name__=="__main__":
    unittest.main()
