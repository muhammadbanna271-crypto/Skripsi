from django.urls import path

from apps.master.views.variable_config_views import (
    ActivateLayerView,
    AddLayerView,
    DeactivateLayerView,
    MoveVariableView,
    RemoveLayerView,
    ReorderVariableView,
    VariableConfigView,
)

urlpatterns = [
    path(
        "variables/config/",
        VariableConfigView.as_view(),
        name="variable-config",
    ),
    path(
        "variables/reorder/",
        ReorderVariableView.as_view(),
        name="variable-reorder",
    ),
    path(
        "variables/move/",
        MoveVariableView.as_view(),
        name="variable-move",
    ),
    path(
        "mediator-layers/add/",
        AddLayerView.as_view(),
        name="layer-add",
    ),
    path(
        "mediator-layers/<int:layer_id>/deactivate/",
        DeactivateLayerView.as_view(),
        name="layer-deactivate",
    ),
    path(
        "mediator-layers/<int:layer_id>/activate/",
        ActivateLayerView.as_view(),
        name="layer-activate",
    ),
    path(
        "mediator-layers/<int:layer_id>/remove/",
        RemoveLayerView.as_view(),
        name="layer-remove",
    ),
]
