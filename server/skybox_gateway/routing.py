from django.urls import path
from .consumers import UnityConsumer

websocket_urlpatterns = [
    path("ws/skybox-updates/", UnityConsumer.as_asgi()),
]
