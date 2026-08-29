"""
Halaman itinerary/rundown + unduh Excel.

Boleh diakses semua user login (visitor/staff/superuser). Rundown dibangun
dari ``TripPlanningService`` (deterministik, hanya destinasi active), bukan
hasil karangan bebas.
"""

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.gis.forms import ItineraryRequestForm
from apps.gis.services.itinerary_excel import ItineraryExcelService
from apps.gis.services.trip_planning import TripPlanningService


def _parse_vehicles(value):
    """Parse JSON kendaraan -> list {type, count}; robust thd input kosong."""
    try:
        data = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    vehicles = []
    for item in data:
        if not isinstance(item, dict):
            continue
        vtype = str(item.get("type") or "").strip()
        try:
            count = int(item.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        if vtype and count > 0:
            vehicles.append({"type": vtype, "count": count})
    return vehicles


def _build_params(form):
    """Petakan data form -> parameter TripPlanningService."""
    data = form.cleaned_data
    preferences = [
        p.strip()
        for p in (data.get("preferences") or "").split(",")
        if p.strip()
    ]
    start_date = data.get("start_date")
    return {
        "duration_days": data.get("duration_days") or 1,
        "start_date": start_date.isoformat() if start_date else None,
        "traveler_count": data.get("traveler_count") or 1,
        "transportation": data.get("transportation") or "",
        "vehicles": _parse_vehicles(data.get("vehicles")),
        "budget": data.get("budget"),
        "budget_scope": data.get("budget_scope") or "total",
        "preferences": preferences,
        "elderly": bool(data.get("elderly")),
        "children": bool(data.get("children")),
    }


def _flat_params(params):
    """Params yang siap dirender sebagai hidden input di template."""
    return {
        "duration_days": params["duration_days"],
        "start_date": params["start_date"] or "",
        "traveler_count": params["traveler_count"],
        "transportation": params["transportation"],
        "vehicles": json.dumps(params.get("vehicles") or []),
        "budget": params["budget"] if params["budget"] is not None else "",
        "budget_scope": params["budget_scope"],
        "preferences": ", ".join(params["preferences"]),
        "elderly": "on" if params["elderly"] else "",
        "children": "on" if params["children"] else "",
    }


def itinerary_page(request):
    itinerary = None
    budget = None
    flat_params = None

    form = ItineraryRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        params = _build_params(form)
        itinerary = TripPlanningService.build_itinerary(params)
        budget = TripPlanningService.estimate_budget(params)
        flat_params = _flat_params(params)

    return render(
        request,
        "gis/itinerary.html",
        {
            "form": form,
            "itinerary": itinerary,
            "budget": budget,
            "flat_params": flat_params,
        },
    )


@require_POST
def itinerary_excel(request):
    form = ItineraryRequestForm(request.POST)
    if not form.is_valid():
        return HttpResponse(
            "Parameter itinerary tidak valid.", status=400
        )

    params = _build_params(form)
    content = ItineraryExcelService.build(params)

    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="itinerary_kota_batu.xlsx"'
    )
    return response
