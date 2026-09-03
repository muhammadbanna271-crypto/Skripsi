from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

urlpatterns = [

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
        ),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(
            next_page="login",
        ),
        name="logout",
    ),

    path(
        "",
        include(
            ("apps.dashboard.urls", "dashboard"),
            namespace="dashboard",
        ),
    ),

    path(
        "master/",
        include(
            ("apps.master.urls", "master"),
            namespace="master",
        ),
    ),

    path(
        "survey/",
        include(
            ("apps.survey.urls", "survey"),
            namespace="survey",
        ),
    ),

    path(
        "respondent/",
        include(
            ("apps.respondent.urls", "respondent"),
            namespace="respondent",
        ),
    ),

    path(
        "response/",
        include(
            ("apps.response.urls", "response"),
            namespace="response",
        ),
    ),

    path(
        "analytics/",
        include(
            ("apps.analytics.urls", "analytics"),
            namespace="analytics",
        ),
    ),

    path(
        "recommendation/",
        include(
            ("apps.recommendation.urls", "recommendation"),
            namespace="recommendation",
        ),
    ),

    path(
        "chatbot/",
        include(
            ("apps.chatbot.urls", "chatbot"),
            namespace="chatbot",
        ),
    ),

    path(
        "gis/",
        include(
            ("apps.gis.urls", "gis"),
            namespace="gis",
        ),
    ),

    path(
        "survey-analysis/",
        include(
            ("apps.survey_analysis.ui.urls", "survey_analysis"),
            namespace="survey_analysis",
        ),
    ),
]