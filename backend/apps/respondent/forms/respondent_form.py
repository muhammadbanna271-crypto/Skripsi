from django import forms

from common.forms import BootstrapModelForm

from apps.respondent.models import Respondent


class RespondentForm(BootstrapModelForm):

    class Meta:

        model = Respondent

        exclude = [

            "nik",

            "latitude",

            "longitude",

        ]

        widgets = {

            "birth_date": forms.DateInput(

                attrs={

                    "type": "date",

                }

            ),

            "occupation": forms.TextInput(

                attrs={

                    "placeholder": "Contoh : Petani",

                }

            ),

            "name": forms.TextInput(

                attrs={

                    "placeholder": "Nama Lengkap",

                }

            ),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if "survey_village" in self.fields:

            self.fields["survey_village"].disabled = False

        if "name" in self.fields:

            self.fields["name"].label = "Nama"

        if "gender" in self.fields:

            self.fields["gender"].label = "Jenis Kelamin"

        if "birth_date" in self.fields:

            self.fields["birth_date"].label = "Tanggal Lahir"

        if "occupation" in self.fields:

            self.fields["occupation"].label = "Pekerjaan"

        if "survey_village" in self.fields:

            self.fields["survey_village"].label = "Desa"