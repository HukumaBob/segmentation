from django.urls import path
from . import views

app_name = 'nettrain'
urlpatterns = [
    path('start_training/', views.start_training_view, name='start_training'),
]