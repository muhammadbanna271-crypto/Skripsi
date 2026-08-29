from apps.response.services import TOPSISService


class RecommendationService:

    @staticmethod
    def generate():

        ranking = TOPSISService.calculate()

        ranking = sorted(

            ranking,

            key=lambda x: x["score"],

            reverse=True,

        )

        return ranking