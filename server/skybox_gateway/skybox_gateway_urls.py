from django.urls import path
from .skybox_gateway_views import doodle_from_skybox, generate_from_skybox, generate_skybox_with_image, inpainting_from_skybox, skybox_webhook

app_name = 'skybox_gateway'

urlpatterns = [
    path('generate', generate_from_skybox),
    path('doodle', doodle_from_skybox),
    path('inpainting', inpainting_from_skybox),
    path("generate_with_image/", generate_skybox_with_image, name="generate_skybox_with_image"),
    path("webhook/", skybox_webhook, name="skybox_webhook"),
]
