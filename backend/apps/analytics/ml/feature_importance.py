import numpy as np
from sklearn.ensemble import RandomForestClassifier


def compute_feature_importance(
    X,
    labels,
    feature_names,
    random_state=42,
):
    """
    Latih Random Forest SUPERVISED dengan target = label cluster
    hasil K-Means, untuk mengetahui indikator mana yang paling
    membedakan antar cluster (bukan untuk prediksi produksi).

    Return: list of dict [{ "feature": ..., "importance": 0.xx }]
    diurutkan dari yang paling dominan.
    """

    X = np.array(X, dtype=float)

    labels = np.array(labels)

    if len(set(labels.tolist())) < 2:
        # RandomForest butuh minimal 2 kelas untuk bisa membedakan
        return []

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=random_state,
    )

    model.fit(X, labels)

    importances = model.feature_importances_

    result = [

        {

            "feature": name,

            "importance": float(score),

        }

        for name, score in zip(feature_names, importances)

    ]

    result.sort(
        key=lambda item: item["importance"],
        reverse=True,
    )

    return result


def aggregate_importance_by_group(
    feature_importance,
    feature_to_group,
):
    """
    feature_importance: hasil dari compute_feature_importance()
    feature_to_group: dict {feature_name: group_name}
                       (misal indikator -> variable/code)

    Menjumlahkan importance per grup lalu dinormalisasi jadi
    persentase (total = 100%), contoh output:

    [{"group": "X1", "percentage": 32.4}, ...]
    """

    totals = {}

    for item in feature_importance:

        group = feature_to_group.get(
            item["feature"],
            item["feature"],
        )

        totals[group] = (
            totals.get(group, 0)
            + item["importance"]
        )

    grand_total = sum(totals.values()) or 1

    result = [

        {

            "group": group,

            "percentage": round(
                (value / grand_total) * 100,
                2,
            ),

        }

        for group, value in totals.items()

    ]

    result.sort(
        key=lambda item: item["percentage"],
        reverse=True,
    )

    return result
