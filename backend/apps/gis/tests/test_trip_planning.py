from datetime import date, timedelta

from django.test import TestCase

from apps.gis.models import (
    RegionElevation,
    TouristDestination,
    TourismCategory,
)
from apps.gis.services.distance import haversine_km, havsum
from apps.gis.services.geo_service import GeoJSONService
from apps.gis.services.trip_planning import TripPlanningService
from apps.master.models import District, Village


class DistanceTest(TestCase):

    def test_haversine_known_distance(self):
        # 1 derajat longitude di ekuator ~= 111.19 km.
        distance = haversine_km(0, 0, 0, 1)
        self.assertIsNotNone(distance)
        self.assertAlmostEqual(distance, 111.19, delta=0.2)

    def test_haversine_invalid_coords_returns_none(self):
        self.assertIsNone(haversine_km(None, 0, 0, 1))
        self.assertIsNone(haversine_km(0, 0, "abc", 1))


class GeoJSONServiceTest(TestCase):

    def test_village_geojson_empty_when_no_file_data(self):
        # File placeholder valid tapi kosong -> bukan error, hanya
        # FeatureCollection kosong tanpa polygon palsu.
        result = GeoJSONService.village_geojson()
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(len(result["features"]), 0)
        self.assertFalse(result["status"]["has_geojson"])

    def test_cluster_legend_has_distinct_colors(self):
        # Tidak ada desa ter-cluster di test DB -> legend kosong tapi valid.
        result = GeoJSONService.cluster_legend()
        self.assertIsInstance(result, list)


class TripPlanningServiceTest(TestCase):

    def setUp(self):
        self.district = District.objects.create(code="T1", name="Test Kecamatan")
        self.village = Village.objects.create(
            code="T1V1",
            name="Desa Test",
            district=self.district,
            latitude=-7.8695,
            longitude=112.5236,
        )
        self.nature = TourismCategory.objects.create(name="wisata alam")
        self.waterfall = TourismCategory.objects.create(name="air terjun")
        self.culture = TourismCategory.objects.create(name="budaya")

    def _destination(self, name, **kwargs):
        defaults = {
            "name": name,
            "village": self.village,
            "latitude": -7.8695,
            "longitude": 112.5236,
            "ticket_price_weekday": 15000,
            "parking_cost": 5000,
            "estimated_duration_minutes": 120,
        }
        defaults.update(kwargs)
        dest = TouristDestination.objects.create(**defaults)
        return dest

    def test_search_filters_by_category(self):
        d1 = self._destination("Coban Test")
        d1.categories.add(self.waterfall)
        d2 = self._destination("Museum Test")
        d2.categories.add(self.culture)

        result = TripPlanningService.search_destinations(
            {"categories": ["air terjun"]}
        )
        names = [r["name"] for r in result["results"]]
        self.assertIn("Coban Test", names)
        self.assertNotIn("Museum Test", names)

    def test_preference_match_prefers_matching_destination(self):
        d1 = self._destination("Air Terjun A", tourism_type="alam")
        d1.categories.add(self.waterfall)
        d2 = self._destination("Museum B", tourism_type="budaya")
        d2.categories.add(self.culture)

        result = TripPlanningService.search_destinations(
            {"preferences": ["nature", "waterfall"]}
        )
        ranked = [r["name"] for r in result["results"]]
        self.assertIn("Air Terjun A", ranked)
        self.assertLess(ranked.index("Air Terjun A"), ranked.index("Museum B"))

    def test_elderly_prefers_elderly_friendly(self):
        d1 = self._destination("Taman Ramah Lansia", elderly_friendly=True)
        d2 = self._destination("Tracking Sulit", elderly_friendly=False,
                                difficulty="hard")

        result = TripPlanningService.search_destinations(
            {"elderly": True}
        )
        ranked = [r["name"] for r in result["results"]]
        self.assertLess(
            ranked.index("Taman Ramah Lansia"),
            ranked.index("Tracking Sulit"),
        )

    def test_budget_estimation_separates_known_and_unknown(self):
        d1 = self._destination("Destinasi A", ticket_price_weekday=20000, parking_cost=5000)
        d2 = self._destination("Destinasi B", ticket_price_weekday=None, ticket_price_weekend=None, parking_cost=None)

        budget = TripPlanningService.estimate_budget(
            {"destination_ids": [d1.id, d2.id]}
        )

        self.assertEqual(budget["known_total"], 25000)
        self.assertEqual(len(budget["known_breakdown"]), 1)
        self.assertEqual(len(budget["unknown_items"]), 1)
        self.assertEqual(budget["unknown_items"][0]["name"], "Destinasi B")
        self.assertIn("belum tersedia", budget["unknown_items"][0]["reason"])

    def test_itinerary_builds_days(self):
        d1 = self._destination("Destinasi A")
        d2 = self._destination("Destinasi B")

        itinerary = TripPlanningService.build_itinerary(
            {"duration_days": 2, "destination_ids": [d1.id, d2.id]}
        )
        self.assertEqual(itinerary["duration_days"], 2)
        self.assertEqual(len(itinerary["days"]), 2)
        scheduled = [
            item
            for day in itinerary["days"]
            for item in day["items"]
            if item["type"] == "destination"
        ]
        self.assertEqual(len(scheduled), 2)

    def test_budget_missing_prices_are_not_invented(self):
        d = self._destination("Tanpa Harga", ticket_price_weekday=None, ticket_price_weekend=None, parking_cost=None)
        budget = TripPlanningService.estimate_budget(
            {"destination_ids": [d.id]}
        )
        self.assertEqual(budget["known_total"], 0)
        self.assertEqual(len(budget["unknown_items"]), 1)

    def test_weekend_price_used_on_weekend_date(self):
        # Cari hari Sabtu terdekat (dinamis, tanpa hard-code tanggal).
        day = date(2026, 8, 25)
        while day.weekday() != 5:
            day += timedelta(days=1)

        dest = self._destination(
            "Wisata Weekend",
            ticket_price_weekday=10000,
            ticket_price_weekend=30000,
            parking_cost=0,
        )
        budget = TripPlanningService.estimate_budget(
            {"destination_ids": [dest.id], "start_date": day.isoformat()}
        )
        self.assertEqual(budget["known_total"], 30000)

    def test_weekday_price_used_on_weekday_date(self):
        day = date(2026, 8, 25)
        while day.weekday() >= 5:
            day += timedelta(days=1)

        dest = self._destination(
            "Wisata Weekday",
            ticket_price_weekday=10000,
            ticket_price_weekend=30000,
            parking_cost=0,
        )
        budget = TripPlanningService.estimate_budget(
            {"destination_ids": [dest.id], "start_date": day.isoformat()}
        )
        self.assertEqual(budget["known_total"], 10000)

    def test_route_order_is_nearest_neighbor(self):
        origin = {"lat": -7.8695, "lon": 112.5236}
        near_a = self._destination("A", latitude=-7.8700, longitude=112.5240)
        far_b = self._destination("B", latitude=-7.9000, longitude=112.5800)
        near_c = self._destination("C", latitude=-7.8710, longitude=112.5250)

        ordered, total_km = TripPlanningService._order_route(
            origin, [far_b, near_a, near_c]
        )
        names = [d.name for d in ordered]

        # Destinasi jauh (B) harus di urutan terakhir.
        self.assertEqual(names[-1], "B")
        self.assertIn(names[0], ["A", "C"])
        self.assertGreater(total_km, 0)
