import math

from apps.master.models import Village
from apps.response.models import Response


class TOPSISService:

    @staticmethod
    def calculate():

        villages = Village.objects.all()

        result = []

        for village in villages:

            responses = (
                Response.objects
                .filter(
                    respondent__village=village
                )
            )

            score = 0

            for response in responses:

                if response.answer_boolean:

                    score += 1

                score += response.answer_integer or 0
                score += float(response.answer_decimal or 0)

            result.append({

                "village": village,

                "score": score,

            })

        return result