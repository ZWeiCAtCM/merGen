from django.urls import path
from .skybox_gateway_views import inpainting_from_segmind, doodle_from_skybox, generate_from_skybox, generate_skybox_with_image, skybox_webhook

app_name = 'skybox_gateway'

urlpatterns = [
    path('generate', generate_from_skybox),
    path('doodle', doodle_from_skybox),
    path("generate_with_image/", generate_skybox_with_image, name="generate_skybox_with_image"),
    path("inpainting/", inpainting_from_segmind, name="inpainting_from_segmind"),
    path("webhook/", skybox_webhook, name="skybox_webhook"),
]
