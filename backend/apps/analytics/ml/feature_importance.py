import numpy as np


def compute_feature_importance(X, labels, feature_names):
    """Ukur seberapa kuat tiap fitur membedakan antar cluster (eta-squared).

    NON-sirkular: menghitung rasio varians antar-cluster terhadap varians
    total per fitur (ANOVA eta-squared / between-cluster variance), BUKAN
    melatih classifier supervised (RandomForest) untuk menebak label cluster —
    yang sirkular karena label berasal dari fitur yang sama.

    Return: list of dict [{ "feature": ..., "importance": 0.xx }],
    dinormalisasi agar total = 1.0, terurut dari yang paling membedakan.
    """

    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels)

    if len(set(labels.tolist())) < 2:
        return []

    grand_mean = X.mean(axis=0)
    total_ss = ((X - grand_mean) ** 2).sum(axis=0)

    between_ss = np.zeros(X.shape[1])
    for c in np.unique(labels):
        mask = labels == c
        cluster_mean = X[mask].mean(axis=0)
        between_ss += mask.sum() * ((cluster_mean - grand_mean) ** 2)

    # eta^2 = SS_between / SS_total (0 bila fitur konstan).
    denom = np.where(total_ss == 0, 1.0, total_ss)
    eta_sq = between_ss / denom

    total = eta_sq.sum()
    if total <= 0:
        weights = np.full(X.shape[1], 1.0 / X.shape[1])
    else:
        weights = eta_sq / total

    result = [
        {"feature": name, "importance": float(score)}
        for name, score in zip(feature_names, weights)
    ]
    result.sort(key=lambda item: item["importance"], reverse=True)
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
