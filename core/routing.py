from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/interview/', consumers.InterviewConsumer.as_asgi()),
    path('ws/dashboard/', consumers.DashboardConsumer.as_asgi()),
]