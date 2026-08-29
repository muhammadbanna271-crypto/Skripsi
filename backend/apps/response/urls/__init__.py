from django.urls import include, path

from .response_urls import urlpatterns as response_urls

urlpatterns = [

    path(
        "",
        include(response_urls),
    ),

]