# llama_gateway_urls.py

from django.urls import path
from . import llama_gateway_views

urlpatterns = [
    path('chat/', llama_gateway_views.chat_proxy, name='chat_proxy'),
    path('list_items/', llama_gateway_views.list_items_proxy, name='list_items_proxy'),
    path('suggest_alternatives/', llama_gateway_views.suggest_alternatives_proxy, name='suggest_alternatives_proxy'),
    path('retrieve_images/', llama_gateway_views.retrieve_images_proxy, name='retrieve_images_proxy'),
]
