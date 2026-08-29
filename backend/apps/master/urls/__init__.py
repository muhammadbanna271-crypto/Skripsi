from django.urls import include, path
from .variable_urls import urlpatterns as variable_urls
from .cluster_urls import urlpatterns as cluster_urls
from .district_urls import urlpatterns as district_urls
from .village_urls import urlpatterns as village_urls
from .indicator_urls import urlpatterns as indicator_urls
from .questionnaire_urls import urlpatterns as questionnaire_urls
from .variable_config_urls import urlpatterns as variable_config_urls

urlpatterns = [

    path("", include(district_urls)),
    path("", include(village_urls)),
    path("", include(cluster_urls)),
    path("", include(variable_urls)),
    path("", include(indicator_urls)),
    path("", include(questionnaire_urls)),
    path("", include(variable_config_urls)),

]