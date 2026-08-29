from common.forms import BootstrapModelForm

from apps.master.models import Questionnaire


class QuestionnaireForm(BootstrapModelForm):

    class Meta:

        model = Questionnaire

        fields = (
            "indicator",
            "question",
            "answer_type",
            "question_order",
            "is_required",
            "is_active",
        )