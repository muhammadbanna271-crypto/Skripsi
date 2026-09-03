"""Test klasifikasi cuaca (bias basah) + metadata prakiraan 6 jam."""

from django.test import SimpleTestCase

from apps.gis.services.geo_service import _classify_weather, _weather_info


class ClassifyWeatherTest(SimpleTestCase):
    """Ambang klasifikasi harus mencerminkan bias basah (wet bias):

    - cepat berstatus "hujan" (ambang longgar),
    - pelit berstatus "cerah" (ambang ketat),
    - kondisi meragukan jatuh ke "mendung".
    """

    def test_clear_sky_is_cerah(self):
        # Langit cerah, awan sedikit, risiko hujan kecil -> cerah.
        self.assertEqual(_classify_weather(0, 0, 0.0, 5), "cerah")
        self.assertEqual(_classify_weather(1, 10, 0.0, 20), "cerah")

    def test_rain_wmo_code_is_hujan(self):
        for code in (51, 61, 63, 80, 95):
            self.assertEqual(
                _classify_weather(code, 90, 1.0, 100), "hujan", f"code={code}"
            )

    def test_high_precip_probability_is_hujan_even_if_clear_code(self):
        # Bias basah: probabilitas hujan >= 60% -> hujan, meski kode cerah.
        self.assertEqual(_classify_weather(0, 75, 0.0, 5), "hujan")

    def test_measurable_precipitation_is_hujan(self):
        self.assertEqual(_classify_weather(0, 10, 0.2, 5), "hujan")

    def test_moderate_precip_probability_not_cerah(self):
        # Probabilitas 40% -> tidak boleh bilang cerah (bias basah) -> mendung.
        self.assertEqual(_classify_weather(0, 40, 0.0, 10), "mendung")

    def test_overcast_is_mendung(self):
        self.assertEqual(_classify_weather(3, 20, 0.0, 90), "mendung")

    def test_high_cloud_cover_is_mendung(self):
        # Partly cloudy (kode 2) tapi awan tebal -> mendung.
        self.assertEqual(_classify_weather(2, 10, 0.0, 80), "mendung")

    def test_no_signal_defaults_to_mendung(self):
        # Tanpa data sama sekali jangan berani bilang cerah.
        self.assertEqual(
            _classify_weather(None, None, None, None), "mendung"
        )


class WeatherInfoTest(SimpleTestCase):

    def test_weather_info_mapping(self):
        self.assertEqual(
            _weather_info("cerah"),
            {"kategori": "cerah", "label": "Cerah", "ikon": "sun"},
        )
        self.assertEqual(
            _weather_info("mendung"),
            {"kategori": "mendung", "label": "Mendung", "ikon": "cloud"},
        )
        self.assertEqual(
            _weather_info("hujan"),
            {"kategori": "hujan", "label": "Hujan", "ikon": "rain"},
        )

    def test_unknown_falls_back_to_mendung(self):
        self.assertEqual(_weather_info("badai"), _weather_info("mendung"))
