from django import forms

from common.forms import BootstrapModelForm

from apps.response.models import Response


class ResponseForm(BootstrapModelForm):

    class Meta:

        model = Response

        fields = "__all__"


LIKERT_CHOICES = [

    (1, "Sangat Tidak Setuju"),
    (2, "Tidak Setuju"),
    (3, "Netral"),
    (4, "Setuju"),
    (5, "Sangat Setuju"),

]


class DynamicSurveyForm(forms.Form):

    def __init__(self, questionnaires, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for q in questionnaires:

            self.fields[f"question_{q.id}"] = forms.ChoiceField(

                label=q.question,

                choices=LIKERT_CHOICES,

                widget=forms.RadioSelect,

                required=q.is_required,

            )