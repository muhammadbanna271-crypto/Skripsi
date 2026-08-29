from django import forms

from apps.master.models import Village


class VillageForm(forms.ModelForm):

    class Meta:
        model = Village

        fields = [
            "district",
            "cluster",
            "code",
            "name",
            "is_active",
        ]

        labels = {
            "district": "Kecamatan",
            "cluster": "Cluster",
            "code": "Kode Desa",
            "name": "Nama Desa",
            "is_active": "Aktif",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["is_active"].widget.attrs["class"] = "form-check-input"

        self.fields["code"].widget.attrs["placeholder"] = "Masukkan kode desa"
        self.fields["name"].widget.attrs["placeholder"] = "Masukkan nama desa"