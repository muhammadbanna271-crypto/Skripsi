from apps.response.models import Response


class ScoringService:

    @staticmethod
    def calculate(respondent):

        responses = (
            Response.objects
            .filter(
                respondent=respondent
            )
            .select_related(
                "questionnaire",
            )
        )

        total_score = 0

        for response in responses:

            questionnaire = response.questionnaire

            if questionnaire.answer_type == "boolean":

                total_score += 1 if response.answer_boolean else 0

            elif questionnaire.answer_type == "likert":

                total_score += response.answer_integer or 0

            elif questionnaire.answer_type == "integer":

                total_score += response.answer_integer or 0

            elif questionnaire.answer_type == "decimal":

                total_score += float(
                    response.answer_decimal or 0
                )

        return total_score