from django.urls import path
from . import views

urlpatterns = [
    path('sequence/<int:sequence_id>/edit/', views.edit_sequence, name='edit_sequence'),
]
