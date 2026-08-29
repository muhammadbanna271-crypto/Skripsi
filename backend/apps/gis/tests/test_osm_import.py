from datetime import date, timedelta

from django.test import TestCase

from apps.gis.models import TouristDestination
from apps.gis.services import osm_import
from apps.gis.services.trip_planning import TripPlanningService
from apps.master.models import District, Village


class ParseOpeningHoursTest(TestCase):

    def test_24_7_is_open_every_day(self):
        self.assertEqual(
            osm_import.parse_opening_hours("24/7"),
            ([], None, None),
        )

    def test_weekday_only(self):
        # Senin-Jumat 08:00-16:00 -> tutup Sabtu & Minggu.
        self.assertEqual(
            osm_import.parse_opening_hours("Mo-Fr 08:00-16:00"),
            ([5, 6], 480, 960),
        )

    def test_every_day_range(self):
        self.assertEqual(
            osm_import.parse_opening_hours("Mo-Su 08:00-17:00"),
            ([], 480, 1020),
        )

    def test_weekend_only(self):
        self.assertEqual(
            osm_import.parse_opening_hours("Sa-Su 08:00-18:00"),
            ([0, 1, 2, 3, 4], 480, 1080),
        )

    def test_no_day_prefix_means_every_day(self):
        self.assertEqual(
            osm_import.parse_opening_hours("08:00-17:00"),
            ([], 480, 1020),
        )

    def test_multiple_time_ranges_uses_min_max(self):
        # Buka Senin-Jumat dengan jeda makan siang.
        self.assertEqual(
            osm_import.parse_opening_hours("Mo-Fr 08:00-12:00,13:00-18:00"),
            ([5, 6], 480, 1080),
        )

    def test_public_holiday_rule_ignored(self):
        self.assertEqual(
            osm_import.parse_opening_hours(
                "Mo-Su 08:00-17:00; PH 09:00-17:00"
            ),
            ([], 480, 1020),
        )

    def test_unknown_when_empty(self):
        self.assertEqual(
            osm_import.parse_opening_hours(""),
            (None, None, None),
        )

    def test_unknown_when_unparseable(self):
        self.assertEqual(
            osm_import.parse_opening_hours("by appointment"),
            (None, None, None),
        )


class MapTourismTypeTest(TestCase):

    def test_theme_park(self):
        self.assertEqual(
            osm_import.map_tourism_type({"tourism": "theme_park"}),
            ("taman rekreasi", ["keluarga", "taman rekreasi"]),
        )

    def test_waterfall(self):
        self.assertEqual(
            osm_import.map_tourism_type({"natural": "waterfall"}),
            ("air terjun", ["alam", "air terjun"]),
        )

    def test_unknown(self):
        self.assertEqual(osm_import.map_tourism_type({}), (None, []))


class ClosedDaysModelTest(TestCase):

    def setUp(self):
        self.district = District.objects.create(code="T1", name="Test")
        self.village = Village.objects.create(
            code="T1V1",
            name="Desa Test",
            district=self.district,
            latitude=-7.8695,
            longitude=112.5236,
        )

    def _dest(self, name, **kwargs):
        return TouristDestination.objects.create(
            name=name,
            village=self.village,
            **kwargs,
        )

    def test_closed_days_display(self):
        self.assertEqual(
            self._dest("A", closed_days=[5, 6]).closed_days_display,
            "Tutup: Sabtu, Minggu",
        )
        self.assertEqual(
            self._dest("B", closed_days=[]).closed_days_display,
            "Buka setiap hari",
        )
        self.assertEqual(
            self._dest("C", closed_days=None).closed_days_display,
            "Belum diketahui",
        )

    def test_is_open_on(self):
        monday = date(2026, 8, 24)
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        saturday = monday + timedelta(days=5)

        closed_weekend = self._dest("A", closed_days=[5, 6])
        self.assertTrue(closed_weekend.is_open_on(monday))
        self.assertFalse(closed_weekend.is_open_on(saturday))

        unknown = self._dest("U", closed_days=None)
        self.assertIsNone(unknown.is_open_on(monday))

    def test_is_open_every_day(self):
        self.assertTrue(self._dest("A", closed_days=[]).is_open_every_day)
        self.assertFalse(self._dest("B", closed_days=[5, 6]).is_open_every_day)
        self.assertFalse(self._dest("C", closed_days=None).is_open_every_day)


class ItineraryClosedDaysTest(TestCase):

    def setUp(self):
        self.district = District.objects.create(code="T1", name="Test")
        self.village = Village.objects.create(
            code="T1V1",
            name="Desa Test",
            district=self.district,
            latitude=-7.8695,
            longitude=112.5236,
        )

    def _dest(self, name, **kwargs):
        defaults = {
            "name": name,
            "village": self.village,
            "latitude": -7.8695,
            "longitude": 112.5236,
            "estimated_duration_minutes": 60,
        }
        defaults.update(kwargs)
        return TouristDestination.objects.create(**defaults)

    @staticmethod
    def _weekday(day_of_week):
        day = date(2026, 8, 24)
        while day.weekday() != day_of_week:
            day += timedelta(days=1)
        return day

    @staticmethod
    def _scheduled_names(result):
        return [
            item["name"]
            for day in result["days"]
            for item in day["items"]
            if item["type"] == "destination"
        ]

    def test_closed_on_trip_day_is_unscheduled(self):
        monday = self._weekday(0)
        dest = self._dest("Tutup Senin", closed_days=[0])

        result = TripPlanningService.build_itinerary({
            "duration_days": 1,
            "start_date": monday.isoformat(),
            "destination_ids": [dest.id],
        })

        self.assertEqual(self._scheduled_names(result), [])
        self.assertEqual(len(result["unscheduled"]), 1)
        self.assertIn("tutup", result["unscheduled"][0]["note"])

    def test_open_on_trip_day_is_scheduled(self):
        monday = self._weekday(0)
        dest = self._dest("Buka Senin", closed_days=[5, 6])

        result = TripPlanningService.build_itinerary({
            "duration_days": 1,
            "start_date": monday.isoformat(),
            "destination_ids": [dest.id],
        })

        self.assertEqual(self._scheduled_names(result), ["Buka Senin"])
