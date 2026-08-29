from apps.master.models import Questionnaire
from apps.master.services.variable_configuration_service import (
    VariableConfigurationService,
)


class ResponseService:
    """
    Service untuk mengambil data questionnaire.
    """

    @staticmethod
    def get_questionnaires():

        return (
            Questionnaire.objects
            .select_related(
                "indicator",
                "indicator__variable",
                "indicator__variable__mediator_layer",
            )
            .filter(
                is_active=True,
                indicator__is_active=True,
                indicator__variable__is_active=True,
            )
            .order_by(
                *VariableConfigurationService.questionnaire_ordering()
            )
        )