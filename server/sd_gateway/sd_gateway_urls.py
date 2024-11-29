from django.urls import path
from .sd_gateway_views import img2img_sd, txt2img_sd, inpainting_from_sd

app_name = 'sd_gateway'

urlpatterns = [
    path('txt2img', txt2img_sd),
    path('img2img', img2img_sd),
    path('inpainting', inpainting_from_sd),
]
