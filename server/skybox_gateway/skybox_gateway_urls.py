from django.urls import path
from .skybox_gateway_views import doodle_from_skybox, generate_from_skybox, inpainting_from_skybox

app_name = 'skybox_gateway'

urlpatterns = [
    path('generate', generate_from_skybox),
    path('doodle', doodle_from_skybox),
    path('inpainting', inpainting_from_skybox),
]
