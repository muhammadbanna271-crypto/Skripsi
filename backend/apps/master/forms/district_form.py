from common.forms import BootstrapModelForm

from apps.master.models import District


class DistrictForm(BootstrapModelForm):

    class Meta:
        model = District

        fields = (
            "code",
            "name",
        )