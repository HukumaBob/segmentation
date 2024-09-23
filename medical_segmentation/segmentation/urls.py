from django.urls import path
from . import views

urlpatterns = [
    path('upload-multiple/', views.upload_multiple_images, name='upload_multiple_images'),
    path('', views.image_list, name='image_list'),
]
