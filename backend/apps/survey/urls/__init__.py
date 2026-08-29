from .survey_urls import urlpatterns as survey_patterns
from .survey_village_urls import urlpatterns as survey_village_patterns

urlpatterns = (
    survey_patterns
    + survey_village_patterns
)