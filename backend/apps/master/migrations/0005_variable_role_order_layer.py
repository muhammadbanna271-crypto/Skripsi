# Generated manually — dynamic variable modeling (role/order/mediator_layer).

import django.db.models.deletion
from django.db import migrations, models


def _role_for_code(code):
    """Mapping code lama -> (role, mediator_layer_number).

    Sesuai PROJECT_BIBLE:
      X1..X5 = predictor (independent)
      Y1..Y3 = mediator layer 1
      Y4..Y6 = response / dependent
    """
    if code.startswith("X"):
        return "predictor", None
    if code.startswith("Y"):
        num = int(code[1:])
        if num <= 3:
            return "mediator", 1
        return "response", None
    return "predictor", None


ROLE_PREFIX = {
    "predictor": "X",
    "mediator": "Y",
    "response": "Z",
}


def map_variable_roles(apps, schema_editor):
    """
    Isi field role/order/mediator_layer untuk data existing, lalu
    regenerate code variable (Y4..Y6 -> Z1..Z3) dan code indicator
    (prefix mengikuti variable). Non-destruktif: id dan relasi
    Questionnaire->Indicator->Variable tidak berubah.
    """
    Variable = apps.get_model("master", "Variable")
    Indicator = apps.get_model("master", "Indicator")
    MediatorLayer = apps.get_model("master", "MediatorLayer")

    # Layer 1 dibuat dulu untuk menampung Y1..Y3.
    layer_1, _ = MediatorLayer.objects.get_or_create(
        number=1,
        defaults={"name": "", "is_active": True},
    )

    variables = list(Variable.objects.all().order_by("code"))

    role_counter = {"predictor": 0, "mediator": 0, "response": 0}
    new_codes = {}

    for var in variables:
        role, layer_number = _role_for_code(var.code)

        var.role = role
        var.mediator_layer = (
            layer_1 if role == "mediator" and layer_number else None
        )

        role_counter[role] += 1
        var.order = role_counter[role]

        new_codes[var.id] = f"{ROLE_PREFIX[role]}{role_counter[role]}"

    # Two-pass supaya tidak bentrok dengan unique constraint `code`:
    # pertama ganti ke nilai temporary yang pasti unik, baru final.
    for var in variables:
        var.code = f"__tmp_{var.id}"
        var.save(update_fields=["code"])

    for var in variables:
        var.code = new_codes[var.id]
        var.save(
            update_fields=[
                "code",
                "role",
                "order",
                "mediator_layer",
            ]
        )

    # Regenerate code indicator: prefix mengikuti variable, sub-ordinal
    # (angka setelah titik) dipertahankan. Contoh Y4.8 -> Z1.8.
    for var in variables:
        new_prefix = new_codes[var.id]
        indicators = list(
            Indicator.objects.filter(variable=var).order_by("code")
        )

        for ind in indicators:
            sub = (
                ind.code.rsplit(".", 1)[-1]
                if "." in ind.code
                else ind.code[1:]
            )
            ind.code = f"{new_prefix}.{sub}"
            ind.save(update_fields=["code"])


def unmap_variable_roles(apps, schema_editor):
    """
    Reverse best-effort: kembalikan code variable & indicator ke
    skema lama (predictor X{order}, mediator Y{order}, response
    Y{3+order}). Field role/order/mediator_layer otomatis dihapus
    oleh reverse dari operasi AddField.
    """
    Variable = apps.get_model("master", "Variable")
    Indicator = apps.get_model("master", "Indicator")

    variables = list(Variable.objects.all().order_by("id"))
    old_codes = {}

    for var in variables:
        if var.role == "predictor":
            old_codes[var.id] = f"X{var.order}"
        elif var.role == "mediator":
            old_codes[var.id] = f"Y{var.order}"
        else:
            old_codes[var.id] = f"Y{3 + var.order}"

    for var in variables:
        var.code = f"__tmp_{var.id}"
        var.save(update_fields=["code"])

    for var in variables:
        var.code = old_codes[var.id]
        var.save(update_fields=["code"])

    for var in variables:
        old_prefix = old_codes[var.id]
        indicators = list(
            Indicator.objects.filter(variable=var).order_by("code")
        )
        for ind in indicators:
            sub = (
                ind.code.rsplit(".", 1)[-1]
                if "." in ind.code
                else ind.code[1:]
            )
            ind.code = f"{old_prefix}.{sub}"
            ind.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("master", "0004_alter_questionnaire_answer_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediatorLayer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Updated At"
                    ),
                ),
                (
                    "number",
                    models.PositiveIntegerField(
                        unique=True, verbose_name="Layer Number"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="Layer Name",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, verbose_name="Active"
                    ),
                ),
            ],
            options={
                "verbose_name": "Mediator Layer",
                "verbose_name_plural": "Mediator Layers",
                "db_table": "master_mediator_layer",
                "ordering": ["number"],
            },
        ),
        migrations.AddField(
            model_name="variable",
            name="role",
            field=models.CharField(
                choices=[
                    ("predictor", "Predictor"),
                    ("mediator", "Mediator"),
                    ("response", "Response / Target"),
                ],
                db_index=True,
                default="predictor",
                max_length=20,
                verbose_name="Role",
            ),
        ),
        migrations.AddField(
            model_name="variable",
            name="order",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Urutan variable di dalam rolenya.",
                verbose_name="Order",
            ),
        ),
        migrations.AddField(
            model_name="variable",
            name="mediator_layer",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Layer mediator (1..N). Kosong untuk predictor/response."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="variables",
                to="master.mediatorlayer",
                verbose_name="Mediator Layer",
            ),
        ),
        migrations.AlterModelOptions(
            name="variable",
            options={
                "verbose_name": "Variable",
                "verbose_name_plural": "Variables",
                "ordering": ["id"],
            },
        ),
        migrations.RunPython(map_variable_roles, unmap_variable_roles),
    ]
