from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ManageViewsAuthorizationTest(TestCase):
    """
    Menu "Kelola Data" (CRUD GIS) hanya boleh diakses staff/superuser.
    Visitor (login non-staff) harus ditolak di level backend (redirect),
    bukan hanya disembunyikan di frontend.
    """

    def setUp(self):
        self.visitor = User.objects.create_user(
            username="visitor",
            password="x",
            is_staff=False,
            is_superuser=False,
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="x",
            is_staff=True,
            is_superuser=False,
        )

    def _login(self, client, user):
        client.force_login(user)

    def test_visitor_cannot_access_manage_lists(self):
        self._login(self.client, self.visitor)
        for name in [
            "gis:manage-characteristic-list",
            "gis:manage-elevation-list",
            "gis:manage-category-list",
            "gis:manage-destination-list",
        ]:
            response = self.client.get(reverse(name))
            self.assertEqual(
                response.status_code,
                302,
                f"visitor seharusnya ditolak di {name}",
            )

    def test_visitor_cannot_access_manage_create(self):
        self._login(self.client, self.visitor)
        response = self.client.get(reverse("gis:manage-destination-create"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_access_manage_lists(self):
        self._login(self.client, self.staff)
        for name in [
            "gis:manage-characteristic-list",
            "gis:manage-elevation-list",
            "gis:manage-category-list",
            "gis:manage-destination-list",
        ]:
            response = self.client.get(reverse(name))
            self.assertEqual(
                response.status_code,
                200,
                f"staff seharusnya boleh akses {name}",
            )

    def test_staff_can_access_manage_create(self):
        self._login(self.client, self.staff)
        response = self.client.get(reverse("gis:manage-destination-create"))
        self.assertEqual(response.status_code, 200)
