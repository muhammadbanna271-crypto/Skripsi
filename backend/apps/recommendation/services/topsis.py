import numpy as np


class TOPSIS:

    """
    Technique for Order Preference by Similarity
    to Ideal Solution
    """

    def __init__(
        self,
        matrix,
        weights,
        criteria,
    ):

        self.matrix = np.array(
            matrix,
            dtype=float,
        )

        self.weights = np.array(
            weights,
            dtype=float,
        )

        self.criteria = criteria

    # =========================================================

    def normalize(self):

        denominator = np.sqrt(
            np.sum(
                self.matrix ** 2,
                axis=0,
            )
        )

        denominator = np.where(
            denominator == 0,
            1,
            denominator,
        )

        return self.matrix / denominator

    # =========================================================

    def weighted_matrix(
        self,
        normalized,
    ):

        return normalized * self.weights

    # =========================================================

    def ideal_positive(
        self,
        weighted,
    ):

        ideal = []

        for i, c in enumerate(self.criteria):

            if c == "benefit":

                ideal.append(
                    np.max(
                        weighted[:, i]
                    )
                )

            else:

                ideal.append(
                    np.min(
                        weighted[:, i]
                    )
                )

        return np.array(ideal)

    # =========================================================

    def ideal_negative(
        self,
        weighted,
    ):

        ideal = []

        for i, c in enumerate(self.criteria):

            if c == "benefit":

                ideal.append(
                    np.min(
                        weighted[:, i]
                    )
                )

            else:

                ideal.append(
                    np.max(
                        weighted[:, i]
                    )
                )

        return np.array(ideal)

    # =========================================================

    def distance_positive(
        self,
        weighted,
        ideal,
    ):

        return np.sqrt(
            np.sum(
                (
                    weighted - ideal
                ) ** 2,
                axis=1,
            )
        )

    # =========================================================

    def distance_negative(
        self,
        weighted,
        ideal,
    ):

        return np.sqrt(
            np.sum(
                (
                    weighted - ideal
                ) ** 2,
                axis=1,
            )
        )

    # =========================================================

    def preference(
        self,
        d_positive,
        d_negative,
    ):

        return d_negative / (
            d_positive
            + d_negative
            + 1e-9
        )

    # =========================================================

    def rank(self):

        normalized = self.normalize()

        weighted = self.weighted_matrix(
            normalized
        )

        positive = self.ideal_positive(
            weighted
        )

        negative = self.ideal_negative(
            weighted
        )

        d_positive = self.distance_positive(
            weighted,
            positive,
        )

        d_negative = self.distance_negative(
            weighted,
            negative,
        )

        preference = self.preference(
            d_positive,
            d_negative,
        )

        return {

            "normalized": normalized,

            "weighted": weighted,

            "positive": positive,

            "negative": negative,

            "distance_positive": d_positive,

            "distance_negative": d_negative,

            "preference": preference,

        }