"""JSON API untuk konfigurasi variable dinamis (drag-and-drop).

- GET  config  : siapapun yang login boleh baca (visitor read-only).
- POST mutation: hanya staff/superuser (authorization di backend,
  bukan cuma disembunyikan di frontend).
"""

import json

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.http import JsonResponse
from django.views import View

from apps.master.models import MediatorLayer, Variable
from apps.master.services.variable_configuration_service import (
    ConfigurationError,
    VariableConfigurationService,
)


def _json(data, status=200):
    return JsonResponse(data, status=status)


class _StaffRequiredJsonMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mutation endpoints: staff/superuser only. Return JSON, bukan HTML."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.is_staff or user.is_superuser
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return _json(
                {"success": False, "error": "Login required."},
                status=401,
            )
        return _json(
            {"success": False, "error": "Forbidden."},
            status=403,
        )


def _parse_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


class VariableConfigView(LoginRequiredMixin, View):
    """GET: baca konfigurasi variable + hasil validasi (read-only)."""

    def get(self, request):
        return _json(
            {
                "success": True,
                "config": VariableConfigurationService.load(),
                "layers": [
                    {
                        "id": layer.id,
                        "number": layer.number,
                        "name": layer.name,
                        "is_active": layer.is_active,
                    }
                    for layer in VariableConfigurationService.active_mediator_layers()
                ],
                "errors": VariableConfigurationService.validate_configuration(),
            }
        )


class ReorderVariableView(_StaffRequiredJsonMixin, View):
    """POST: urutkan ulang variable dalam satu role/layer."""

    def post(self, request):
        body = _parse_body(request)
        role = body.get("role")
        ordered_ids = body.get("ordered_ids")
        layer_number = body.get("layer")

        if role not in Variable.ROLE_ORDER:
            return _json(
                {"success": False, "error": "Role tidak valid."},
                status=400,
            )

        if not isinstance(ordered_ids, list):
            return _json(
                {"success": False, "error": "ordered_ids harus berupa list."},
                status=400,
            )

        try:
            config = VariableConfigurationService.reorder(
                role, ordered_ids, layer_number, user=request.user
            )
        except (ConfigurationError, Variable.DoesNotExist) as exc:
            return _json(
                {"success": False, "error": str(exc)},
                status=400,
            )

        return _json({"success": True, "config": config})


class MoveVariableView(_StaffRequiredJsonMixin, View):
    """POST: pindahkan variable antar role / antar layer mediator."""

    def post(self, request):
        body = _parse_body(request)
        variable_id = body.get("variable_id")
        new_role = body.get("new_role")
        layer_number = body.get("layer")
        position = body.get("position")

        if new_role not in Variable.ROLE_ORDER:
            return _json(
                {"success": False, "error": "Role tidak valid."},
                status=400,
            )

        if position is not None:
            try:
                position = int(position)
            except (TypeError, ValueError):
                position = None

        try:
            config = VariableConfigurationService.move(
                variable_id,
                new_role,
                layer_number,
                position=position,
                user=request.user,
            )
        except (ConfigurationError, Variable.DoesNotExist) as exc:
            return _json(
                {"success": False, "error": str(exc)},
                status=400,
            )

        return _json({"success": True, "config": config})


class AddLayerView(_StaffRequiredJsonMixin, View):
    """POST: buat mediator layer baru."""

    def post(self, request):
        body = _parse_body(request)
        name = body.get("name", "")
        layer = VariableConfigurationService.add_layer(
            name=name, user=request.user
        )
        return _json(
            {
                "success": True,
                "layer": {
                    "id": layer.id,
                    "number": layer.number,
                    "name": layer.name,
                    "is_active": layer.is_active,
                },
            }
        )


class DeactivateLayerView(_StaffRequiredJsonMixin, View):
    def post(self, request, layer_id):
        try:
            VariableConfigurationService.deactivate_layer(
                layer_id, user=request.user
            )
        except MediatorLayer.DoesNotExist:
            return _json(
                {"success": False, "error": "Layer tidak ditemukan."},
                status=404,
            )
        return _json({"success": True})


class ActivateLayerView(_StaffRequiredJsonMixin, View):
    def post(self, request, layer_id):
        try:
            VariableConfigurationService.activate_layer(
                layer_id, user=request.user
            )
        except MediatorLayer.DoesNotExist:
            return _json(
                {"success": False, "error": "Layer tidak ditemukan."},
                status=404,
            )
        return _json({"success": True})


class RemoveLayerView(_StaffRequiredJsonMixin, View):
    def post(self, request, layer_id):
        try:
            config = VariableConfigurationService.remove_layer(
                layer_id, user=request.user
            )
        except MediatorLayer.DoesNotExist:
            return _json(
                {"success": False, "error": "Layer tidak ditemukan."},
                status=404,
            )
        return _json({"success": True, "config": config})
