from common.forms import BootstrapModelForm

from apps.master.models import Variable


class VariableForm(BootstrapModelForm):
    """
    ``code`` sengaja TIDAK dimasukkan ke form — code (X1/Y1/Z1)
    di-generate otomatis oleh VariableConfigurationService dari
    role + order. Primary key/internal ID (``id``) tidak berubah.
    """

    class Meta:

        model = Variable

        fields = (
            "name",
            "description",
            "weight",
            "role",
            "order",
            "mediator_layer",
            "is_active",
        )
