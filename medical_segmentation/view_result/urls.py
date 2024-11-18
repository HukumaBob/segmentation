from django.urls import path
from . import views

app_name = 'view_result'  # Задайте имя пространства имён

urlpatterns = [
    path('view_video/', views.view_video, name='view_video'),
]
