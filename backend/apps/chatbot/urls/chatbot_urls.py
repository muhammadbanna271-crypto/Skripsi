from django.urls import path

from apps.chatbot.views import chat_page, chat_message, unlock_claude


urlpatterns = [

    path(
        "",
        chat_page,
        name="chat-page",
    ),

    path(
        "api/message/",
        chat_message,
        name="chat-message",
    ),

    path(
        "api/unlock/",
        unlock_claude,
        name="chat-unlock",
    ),

]
