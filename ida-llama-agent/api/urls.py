# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('list_items/', views.list_items_view, name='list_items'),
    path('suggest_alternatives/', views.suggest_alternatives_view, name='suggest_alternatives'),
    path('retrieve_images/', views.retrieve_images_view, name='retrieve_images'),
    path('chat/', views.chat_view, name='chat'),  # 新增聊天接口
]
