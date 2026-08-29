from django.db.models import Avg, Count

from apps.master.models import Village
from apps.response.models import Response
from apps.respondent.models import Respondent


class AnalyticsService:

    @staticmethod
    def village_scores():
        """
        Rata-rata skor setiap desa.
        """

        data = []

        villages = Village.objects.all().order_by("name")

        for village in villages:

            respondents = Respondent.objects.filter(
                survey_village__village=village
            )

            response_count = Response.objects.filter(
                respondent__in=respondents
            ).count()

            average = (
                Response.objects.filter(
                    respondent__in=respondents
                ).aggregate(
                    avg=Avg("score")
                )["avg"]
                or 0
            )

            data.append({
                "village": village,
                "respondent_count": respondents.count(),
                "response_count": response_count,
                "average_score": round(float(average), 2),
            })

        return data

    @staticmethod
    def average_score():

        return (
            Response.objects.aggregate(
                avg=Avg("score")
            )["avg"]
            or 0
        )

    @staticmethod
    def total_completed_response():

        return Response.objects.count()

    @staticmethod
    def total_respondent():

        return Respondent.objects.count()

    @staticmethod
    def likert_distribution():
        """
        Distribusi jawaban Likert 1-5.
        """

        result = []

        for score in range(1, 6):

            result.append({

                "score": score,

                "label": {
                    1: "Sangat Tidak Setuju",
                    2: "Tidak Setuju",
                    3: "Netral",
                    4: "Setuju",
                    5: "Sangat Setuju",
                }[score],

                "total": Response.objects.filter(
                    answer_integer=score
                ).count(),

            })

        return result

    @staticmethod
    def indicator_scores():
        """
        Rata-rata setiap indikator.
        """

        return (
            Response.objects
            .values(
                "questionnaire__indicator__name"
            )
            .annotate(

                average=Avg("score"),

                total=Count("id"),

            )
            .order_by(
                "questionnaire__indicator__name"
            )
        )