"""
File BARU: backend/common/decorators.py

Dipakai di semua views.py yang punya fungsi create/update/delete,
supaya cuma staff/superuser yang boleh akses. Untuk fungsi list/
detail (cuma nampilin data), TIDAK perlu decorator ini -- cukup
@login_required biasa (semua user yang login boleh lihat).
"""

from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import redirect


def staff_required(view_func):
    """
    Dipasang di atas view create/update/delete. Kalau yang akses
    bukan staff/superuser, di-redirect balik + kasih pesan error
    (bukan error 403 polos, biar user ngerti kenapa).
    """

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):

        if not (request.user.is_staff or request.user.is_superuser):

            messages.error(
                request,
                "Kamu tidak punya izin untuk melakukan aksi ini. "
                "Hubungi admin kalau butuh akses tambahan.",
            )

            # Balik ke halaman sebelumnya, atau ke dashboard
            # kalau tidak ada referer.
            return redirect(
                request.META.get("HTTP_REFERER", "dashboard:dashboard")
            )

        return view_func(request, *args, **kwargs)

    return _wrapped