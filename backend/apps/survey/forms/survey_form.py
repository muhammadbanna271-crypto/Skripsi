from django import forms

from apps.survey.models import Survey


class SurveyForm(forms.ModelForm):

    class Meta:

        model = Survey

        fields = (
            "name",
            "description",
            "start_date",
            "end_date",
            "is_active",
        )

        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"},
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date"},
            ),
        }