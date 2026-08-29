from django import forms

from apps.survey.models import SurveyVillage


class SurveyVillageForm(forms.ModelForm):

    class Meta:

        model = SurveyVillage

        fields = [
            "survey",
            "village",
            "is_active",
        ]

        widgets = {

            "survey": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "village": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),

        }