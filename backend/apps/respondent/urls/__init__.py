from django.urls import include, path

from .respondent_urls import urlpatterns as respondent_urls

urlpatterns = [

    path(
        "",
        include(respondent_urls),
    ),

]