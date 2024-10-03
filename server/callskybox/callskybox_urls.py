from django.urls import path
from .views import doodle_from_skybox, generate_from_skybox, inpainting_from_skybox

app_name = 'callskybox'

urlpatterns = [
    path('generate', generate_from_skybox),
    path('doodle', doodle_from_skybox),
    path('inpainting', inpainting_from_skybox),
]
