from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, reverse


class LoginRequiredMiddleware:
    """
    Memaksa semua halaman login terlebih dahulu, kecuali halaman publik.

    Halaman publik: login/logout, Django admin (punya auth sendiri),
    static & media, chatbot (publik), dan halaman wisata GIS (/gis/).
    View internal (analytics/recommendation/master/survey/respondent/response)
    TIDAK dikecualikan — minimal wajib login, lalu diperketat staff lewat
    mixin/decorator di tiap view.
    """

    # Path prefix yang BOLEH diakses tanpa login (publik).
    public_path_prefixes = (
        "/admin/",
        "/chatbot/",
        "/gis/",
        "/media/",
    )

    # url_name yang boleh diakses tanpa login.
    public_url_names = {"login", "logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path

        # Root (landing visitor) boleh diakses tanpa login.
        if path == "/":
            return self.get_response(request)

        if path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        for prefix in self.public_path_prefixes:
            if path.startswith(prefix):
                return self.get_response(request)

        try:
            url_name = resolve(path).url_name
        except Exception:
            url_name = None

        if url_name in self.public_url_names:
            return self.get_response(request)

        return redirect(f"{reverse('login')}?next={path}")
