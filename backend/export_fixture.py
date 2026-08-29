import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.management import call_command

# Data yang DI-EXCLUDE adalah data hasil komputasi / transient yang
# akan dihitung ulang otomatis setelah load (skor, ML registry, cache
# TOPSIS, audit log, dsb). Yang di-load hanya data master + survey + user.
with open("initial_data.json", "w", encoding="utf-8") as f:
    call_command(
        "dumpdata",
        exclude=[
            "contenttypes",
            "auth.permission",
            "admin.logentry",
            "sessions",
            # Hasil komputasi (dihitung ulang via Retrain / Hitung Ulang):
            "analytics.indicatorscore",
            "analytics.variablescore",
            "analytics.villagescore",
            "analytics.mlmodelregistry",
            "analytics.analysisstate",
            "recommendation.recommendationresult",
            # Data transient:
            "chatbot.chatbotusage",
            "master.variableconfigauditlog",
        ],
        indent=2,
        stdout=f,
    )

print("initial_data.json berhasil dibuat.")
