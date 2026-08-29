from common.forms import BootstrapModelForm

from apps.master.models import Cluster


class ClusterForm(BootstrapModelForm):

    class Meta:

        model = Cluster

        fields = (
            "code",
            "name",
            "description",
        )