from common.forms import BootstrapModelForm

from apps.master.models import Indicator


class IndicatorForm(BootstrapModelForm):

    class Meta:

        model = Indicator

        fields = (
            "variable",
            "code",
            "name",
            "description",
            "weight",
            "is_active",
        )