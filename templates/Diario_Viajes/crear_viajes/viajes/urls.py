from django.urls import path

from . import views

urlpatterns = [
    path('nuevo/', views.crear_viaje, name='crear_viaje'),
]
