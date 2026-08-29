"""Single source of truth untuk konfigurasi variable dinamis.

Semua modul (Indicator UI, Questionnaire, Data mapping, Analysis,
Dashboard) membaca role/order/layer dari sini. Konfigurasi persistent
ada di database (tabel master_variable + master_mediator_layer);
``load()`` hanyalah representasi generated untuk dikonsumsi.
"""

from django.db import transaction
from django.db.models import Case, IntegerField, Max, Q, Value, When

from apps.master.models import Indicator, MediatorLayer, Variable


class ConfigurationError(ValueError):
    """Kesalahan konfigurasi variable yang bisa dipakai user."""


class VariableConfigurationService:
    # =========================================================
    # ORDERING & LOAD
    # =========================================================

    @staticmethod
    def _role_rank_expression(prefix=""):
        def field(name):
            return f"{prefix}{name}" if prefix else name

        return Case(
            When(**{field("role"): Variable.ROLE_PREDICTOR}, then=Value(0)),
            When(**{field("role"): Variable.ROLE_MEDIATOR}, then=Value(1)),
            When(**{field("role"): Variable.ROLE_RESPONSE}, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )

    @classmethod
    def ordering(cls):
        """Urutan kanonik: predictor -> mediator (layer -> order) -> response."""
        return (
            cls._role_rank_expression(),
            "mediator_layer__number",
            "order",
        )

    @classmethod
    def indicator_ordering(cls):
        """Ordering Indicator mengikuti konfigurasi variable-nya."""
        return (
            cls._role_rank_expression("variable__"),
            "variable__mediator_layer__number",
            "variable__order",
            "code",
        )

    @classmethod
    def questionnaire_ordering(cls):
        """Ordering Questionnaire mengikuti konfigurasi variable-nya."""
        return (
            cls._role_rank_expression("indicator__variable__"),
            "indicator__variable__mediator_layer__number",
            "indicator__variable__order",
            "indicator__code",
            "question_order",
        )

    @classmethod
    def ordered_queryset(cls, active_only=True):
        queryset = Variable.objects.select_related("mediator_layer")
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by(*cls.ordering())

    @staticmethod
    def _serialize(variable):
        return {
            "id": variable.id,
            "code": variable.code,
            "name": variable.name,
            "description": variable.description,
            "role": variable.role,
            "order": variable.order,
            "mediator_layer": (
                variable.mediator_layer.number
                if variable.mediator_layer
                else None
            ),
            "weight": float(variable.weight),
            "is_active": variable.is_active,
        }

    @classmethod
    def load(cls, active_only=True):
        """Bentuk analysis_config:

            {
              "predictors": [...],
              "mediator_layers": [[...], [...]],
              "responses": [...],
            }
        """
        config = {
            "predictors": [],
            "mediator_layers": [],
            "responses": [],
        }

        layers = {}

        for variable in cls.ordered_queryset(active_only=active_only):
            item = cls._serialize(variable)

            if variable.role == Variable.ROLE_PREDICTOR:
                config["predictors"].append(item)
                continue

            if variable.role == Variable.ROLE_RESPONSE:
                config["responses"].append(item)
                continue

            # Mediator — hanya layer yang masih aktif yang dihitung.
            layer = variable.mediator_layer
            if layer is None or not layer.is_active:
                continue

            layers.setdefault(layer.number, []).append(item)

        config["mediator_layers"] = [
            layers[number] for number in sorted(layers)
        ]

        return config

    @classmethod
    def variable_buttons(cls):
        """List {code, name} semua variable dalam urutan konfigurasi
        (Predictor -> Mediator -> Response), untuk tombol filter."""
        return [
            {"code": variable.code, "name": variable.name}
            for variable in cls.ordered_queryset(active_only=False)
        ]

    @classmethod
    def group_filter_options(cls):
        """Opsi filter grup: All, Predictor, Mediator Layer N, Response."""
        options = [
            {"value": "", "label": "All"},
            {"value": Variable.ROLE_PREDICTOR, "label": "Predictor"},
        ]
        for layer in MediatorLayer.objects.order_by("number"):
            options.append(
                {
                    "value": f"mediator-{layer.number}",
                    "label": f"Mediator — Layer {layer.number}",
                }
            )
        options.append(
            {"value": Variable.ROLE_RESPONSE, "label": "Response / Target"}
        )
        return options

    @staticmethod
    def filter_by_group(queryset, group):
        """Terapkan filter grup (predictor / mediator-N / response)."""
        if group == Variable.ROLE_PREDICTOR:
            return queryset.filter(role=Variable.ROLE_PREDICTOR)
        if group == Variable.ROLE_RESPONSE:
            return queryset.filter(role=Variable.ROLE_RESPONSE)
        if group and group.startswith("mediator-"):
            try:
                layer_number = int(group.split("-", 1)[1])
            except ValueError:
                return queryset
            return queryset.filter(
                role=Variable.ROLE_MEDIATOR,
                mediator_layer__number=layer_number,
            )
        return queryset

    @classmethod
    def group_variables(cls, variables):
        """Kelompokkan Variable instances menjadi:
            {
              "predictors": [...],
              "mediator_layers": [{"layer": layer|None, "variables": [...]}],
              "responses": [...],
            }
        """
        predictors = []
        responses = []
        layer_map = {}

        for variable in variables:
            if variable.role == Variable.ROLE_PREDICTOR:
                predictors.append(variable)
            elif variable.role == Variable.ROLE_RESPONSE:
                responses.append(variable)
            elif variable.role == Variable.ROLE_MEDIATOR:
                layer = variable.mediator_layer
                key = layer.id if layer else None
                bucket = layer_map.setdefault(
                    key, {"layer": layer, "variables": []}
                )
                bucket["variables"].append(variable)

        mediator_layers = [
            bucket
            for _, bucket in sorted(
                layer_map.items(),
                key=lambda item: (
                    item[1]["layer"].number
                    if item[1]["layer"]
                    else 10 ** 9
                ),
            )
        ]

        return {
            "predictors": predictors,
            "mediator_layers": mediator_layers,
            "responses": responses,
        }

    @classmethod
    def active_mediator_layers(cls):
        return list(
            MediatorLayer.objects
            .filter(is_active=True)
            .order_by("number")
        )

    @classmethod
    def active_indicators(cls):
        """Indicator yang dipakai analysis: indicator & variable aktif,
        dan kalau mediator, layer-nya harus aktif. Mediator di layer
        non-aktif otomatis ter-exclude (Predictor -> Response)."""
        return (
            Indicator.objects
            .filter(is_active=True, variable__is_active=True)
            .filter(
                Q(variable__role=Variable.ROLE_PREDICTOR)
                | Q(variable__role=Variable.ROLE_RESPONSE)
                | Q(
                    variable__role=Variable.ROLE_MEDIATOR,
                    variable__mediator_layer__is_active=True,
                )
            )
            .select_related("variable", "variable__mediator_layer")
            .order_by(*cls.indicator_ordering())
        )

    @classmethod
    def config_signature(cls):
        """Hash deterministik dari konfigurasi yang memengaruhi analysis.

        URUTAN tidak diperhitungkan: reorder/pindah posisi dalam grup yang
        sama (mis. X1 <-> X5, tetap predictor) tidak mengubah substansi
        analysis, sehingga tidak dianggap perubahan. Yang dihitung adalah
        SET variable (role + layer) dan SET indicator (variable + weight
        + criterion_type).
        """
        import hashlib

        from apps.master.models import MediatorLayer

        parts = []

        parts.extend(
            sorted(
                f"ind|{i.id}|{i.variable_id}|{i.weight}|{i.criterion_type}"
                for i in cls.active_indicators()
            )
        )

        parts.extend(
            sorted(
                f"var|{v.id}|{v.role}|{v.mediator_layer_id or 0}"
                for v in cls.ordered_queryset(active_only=True)
            )
        )

        parts.extend(
            sorted(
                f"layer|{l.id}|{l.number}"
                for l in MediatorLayer.objects.filter(is_active=True)
            )
        )

        raw = "\n".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def next_layer_number(cls):
        current = MediatorLayer.objects.aggregate(
            m=Max("number")
        )["m"]
        return (current or 0) + 1

    # =========================================================
    # CODE GENERATION
    # =========================================================

    @classmethod
    @transaction.atomic
    def regenerate_codes(cls):
        """Recompute code X/Y/Z semua variable + prefix code indicator.

        Predictor -> X{n}, Mediator -> Y{n} (global antar layer),
        Response -> Z{n}. ``id`` tidak pernah berubah.
        """
        variables = list(cls.ordered_queryset(active_only=False))

        counters = {
            Variable.ROLE_PREDICTOR: 0,
            Variable.ROLE_MEDIATOR: 0,
            Variable.ROLE_RESPONSE: 0,
        }

        new_variable_codes = {}

        for variable in variables:
            counters[variable.role] += 1
            prefix = Variable.ROLE_CODE_PREFIX[variable.role]
            new_variable_codes[variable.id] = (
                f"{prefix}{counters[variable.role]}"
            )

        indicators = list(
            Indicator.objects
            .select_related("variable")
            .all()
            .order_by("variable_id", "code")
        )

        new_indicator_codes = {}

        for indicator in indicators:
            new_prefix = new_variable_codes[indicator.variable_id]
            sub = cls._indicator_sub_ordinal(indicator.code)
            new_indicator_codes[indicator.id] = f"{new_prefix}.{sub}"

        # Two-pass supaya tidak bentrok unique constraint `code`.
        for variable in variables:
            variable.code = f"__vtmp_{variable.id}"
            variable.save(update_fields=["code"])

        for indicator in indicators:
            indicator.code = f"__itmp_{indicator.id}"
            indicator.save(update_fields=["code"])

        for variable in variables:
            variable.code = new_variable_codes[variable.id]
            variable.save(update_fields=["code"])

        for indicator in indicators:
            indicator.code = new_indicator_codes[indicator.id]
            indicator.save(update_fields=["code"])

        return new_variable_codes

    @staticmethod
    def _indicator_sub_ordinal(code):
        if "." in code:
            return code.rsplit(".", 1)[-1]
        # Fallback: buang prefix huruf (misal "X1" -> "1").
        return code[1:]

    # =========================================================
    # MUTATION OPERATIONS
    # =========================================================

    @classmethod
    @transaction.atomic
    def reorder(cls, role, ordered_ids, layer_number=None, user=None):
        """Urutkan variable dalam satu role (atau satu layer mediator)."""
        if role not in Variable.ROLE_ORDER:
            raise ConfigurationError("Role tidak valid.")

        variables = cls._resolve_group(role, layer_number)

        id_to_var = {v.id: v for v in variables}

        ids = [int(i) for i in ordered_ids]

        if set(ids) != set(id_to_var.keys()):
            raise ConfigurationError(
                "Daftar id tidak cocok dengan variable di grup ini."
            )

        for position, variable_id in enumerate(ids, start=1):
            id_to_var[variable_id].order = position
            id_to_var[variable_id].save(update_fields=["order"])

        cls.regenerate_codes()
        cls.mark_analysis_outdated()
        cls._record_audit(
            user,
            "reorder",
            detail={
                "role": role,
                "layer": layer_number,
                "ordered_ids": ids,
            },
        )
        return cls.load()

    @classmethod
    @transaction.atomic
    def move(cls, variable_id, new_role, layer_number=None, position=None, user=None):
        """Pindahkan variable antar role / antar layer mediator.

        Kalau ``position`` diberikan (1-based), variable disisipkan di posisi
        itu dan variable di bawahnya otomatis digeser (+1). Kalau tidak,
        variable ditambahkan ke urutan paling akhir grup tujuan.
        """
        if new_role not in Variable.ROLE_ORDER:
            raise ConfigurationError("Role tidak valid.")

        variable = Variable.objects.select_related(
            "mediator_layer"
        ).get(pk=variable_id)

        old_role = variable.role
        old_order = variable.order
        old_layer = (
            variable.mediator_layer.number
            if variable.mediator_layer
            else None
        )

        variable.role = new_role

        if new_role == Variable.ROLE_MEDIATOR:
            variable.mediator_layer = cls._get_or_create_layer(
                layer_number
            )
        else:
            variable.mediator_layer = None

        if position is None:
            # Tambah ke urutan paling akhir grup tujuan.
            variable.order = cls._next_order(
                new_role, variable.mediator_layer
            )
        else:
            cls._insert_at(variable, new_role, position)

        variable.save(update_fields=["role", "mediator_layer", "order"])

        new_layer = (
            variable.mediator_layer.number
            if variable.mediator_layer
            else None
        )

        cls.regenerate_codes()
        cls.mark_analysis_outdated()
        cls._record_audit(
            user,
            "move",
            variable=variable,
            old_role=old_role,
            new_role=new_role,
            old_order=old_order,
            new_order=variable.order,
            old_layer=old_layer,
            new_layer=new_layer,
        )
        return cls.load()

    @classmethod
    @transaction.atomic
    def add_layer(cls, name="", user=None):
        layer = MediatorLayer.objects.create(
            number=cls.next_layer_number(),
            name=name,
            is_active=True,
        )
        cls._record_audit(
            user,
            "add_layer",
            detail={"number": layer.number, "name": layer.name},
        )
        return layer

    @classmethod
    def deactivate_layer(cls, layer_id, user=None):
        layer = MediatorLayer.objects.get(pk=layer_id)
        layer.is_active = False
        layer.save(update_fields=["is_active"])
        cls.mark_analysis_outdated()
        cls._record_audit(
            user,
            "deactivate_layer",
            detail={"layer_id": layer.id, "number": layer.number},
        )
        return layer

    @classmethod
    def activate_layer(cls, layer_id, user=None):
        layer = MediatorLayer.objects.get(pk=layer_id)
        layer.is_active = True
        layer.save(update_fields=["is_active"])
        cls.mark_analysis_outdated()
        cls._record_audit(
            user,
            "activate_layer",
            detail={"layer_id": layer.id, "number": layer.number},
        )
        return layer

    @classmethod
    @transaction.atomic
    def remove_layer(cls, layer_id, user=None):
        """Hapus layer. Variable di dalamnya dipindah ke layer
        terdekat; kalau tidak ada, mediator dinonaktifkan (orphan)."""
        layer = MediatorLayer.objects.get(pk=layer_id)
        variables = list(layer.variables.all())

        fallback = (
            MediatorLayer.objects
            .exclude(pk=layer_id)
            .order_by("number")
            .first()
        )

        for variable in variables:
            if fallback is not None:
                variable.mediator_layer = fallback
                variable.order = cls._next_order(
                    Variable.ROLE_MEDIATOR, fallback
                )
                variable.save(update_fields=["mediator_layer", "order"])
            else:
                variable.mediator_layer = None
                variable.is_active = False
                variable.save(
                    update_fields=["mediator_layer", "is_active"]
                )

        layer.delete()
        cls._renumber_layers()
        cls.regenerate_codes()
        cls.mark_analysis_outdated()
        cls._record_audit(
            user,
            "remove_layer",
            detail={"layer_id": layer.id, "number": layer.number},
        )
        return cls.load()

    # =========================================================
    # HELPERS
    # =========================================================

    @classmethod
    def _resolve_group(cls, role, layer_number=None):
        variables = list(
            Variable.objects
            .filter(role=role)
            .order_by("order")
        )

        if role == Variable.ROLE_MEDIATOR:
            layer = cls._get_or_create_layer(layer_number)
            variables = [
                v for v in variables
                if v.mediator_layer_id == layer.id
            ]
        else:
            variables = [v for v in variables if v.mediator_layer_id is None]

        return variables

    @staticmethod
    def _get_or_create_layer(layer_number):
        if layer_number is None:
            raise ConfigurationError(
                "Mediator harus punya layer."
            )
        layer, _ = MediatorLayer.objects.get_or_create(
            number=layer_number,
            defaults={"name": "", "is_active": True},
        )
        return layer

    @staticmethod
    def _next_order(role, layer):
        variables = Variable.objects.filter(role=role)
        if role == Variable.ROLE_MEDIATOR:
            variables = variables.filter(mediator_layer=layer)
        else:
            variables = variables.filter(mediator_layer__isnull=True)
        current = variables.aggregate(m=Max("order"))["m"]
        return (current or 0) + 1

    @staticmethod
    def _insert_at(variable, role, position):
        """Sisipkan variable di ``position`` (1-based) dalam grup tujuannya,
        lalu geser variable dengan order >= position ke bawah (+1)."""
        group = (
            Variable.objects
            .filter(role=role)
            .exclude(id=variable.id)
        )

        if role == Variable.ROLE_MEDIATOR:
            group = group.filter(mediator_layer=variable.mediator_layer)
        else:
            group = group.filter(mediator_layer__isnull=True)

        for existing in (
            group.filter(order__gte=position).order_by("-order")
        ):
            existing.order += 1
            existing.save(update_fields=["order"])

        variable.order = position

    @staticmethod
    def _renumber_layers():
        for index, layer in enumerate(
            MediatorLayer.objects.order_by("number"), start=1
        ):
            if layer.number != index:
                layer.number = index
                layer.save(update_fields=["number"])

    # =========================================================
    # ANALYSIS INVALIDATION
    # =========================================================

    @staticmethod
    def mark_analysis_outdated():
        """(No-op) Staleness kini otomatis terdeteksi lewat perbandingan
        signature konfigurasi (AnalysisState.is_stale()), sehingga kalau
        perubahan di-undo/revert, analysis dianggap valid lagi tanpa perlu
        dihitung ulang. Method ini dipertahankan sebagai hook."""
        pass

    # =========================================================
    # AUDIT
    # =========================================================

    @staticmethod
    def _record_audit(
        user,
        action,
        variable=None,
        old_role="",
        new_role="",
        old_order=None,
        new_order=None,
        old_layer=None,
        new_layer=None,
        detail=None,
    ):
        from apps.master.models import VariableConfigAuditLog

        authenticated = bool(getattr(user, "is_authenticated", False))
        VariableConfigAuditLog.objects.create(
            user=user if authenticated else None,
            action=action,
            variable=variable,
            old_role=old_role,
            new_role=new_role,
            old_order=old_order,
            new_order=new_order,
            old_layer=old_layer,
            new_layer=new_layer,
            detail=detail or {},
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    @classmethod
    def validate_configuration(cls):
        """Kembalikan list error (kosong = valid). Tidak raise."""
        errors = []

        variables = list(
            Variable.objects
            .filter(is_active=True)
            .select_related("mediator_layer")
        )

        if not any(v.role == Variable.ROLE_PREDICTOR for v in variables):
            errors.append("Minimal harus ada satu predictor aktif.")

        if not any(v.role == Variable.ROLE_RESPONSE for v in variables):
            errors.append("Minimal harus ada satu response aktif.")

        # Duplicate order per role / per mediator layer.
        seen_predictor = {}
        seen_response = {}
        seen_mediator = {}

        for variable in variables:
            if variable.role == Variable.ROLE_PREDICTOR:
                bucket = seen_predictor
            elif variable.role == Variable.ROLE_RESPONSE:
                bucket = seen_response
            else:
                key = (
                    variable.mediator_layer.number
                    if variable.mediator_layer
                    else None
                )
                bucket = seen_mediator.setdefault(key, {})

            if variable.order in bucket:
                errors.append(
                    f"Duplicate order {variable.order} pada role "
                    f"{variable.role}."
                )
            bucket[variable.order] = variable

        for variable in variables:
            if variable.role == Variable.ROLE_MEDIATOR:
                if variable.mediator_layer is None:
                    errors.append(
                        f"Mediator '{variable.name}' tidak punya layer."
                    )
                elif not variable.mediator_layer.is_active:
                    # Tidak error — mediator di layer non-aktif di-skip.
                    pass

        return errors
