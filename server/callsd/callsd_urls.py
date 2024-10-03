from django.urls import path
from .views import doodle_from_sd, generate_from_sd, inpainting_from_sd

app_name = 'callskybox'

urlpatterns = [
    path('generate', generate_from_sd),
    path('doodle', doodle_from_sd),
    path('inpainting', inpainting_from_sd),
]
