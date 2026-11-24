"""Stall pages, mounted at /exhibition/ (vyayam_project/urls.py).

Every view here 404s unless settings.EXHIBITION_MODE. Later stall pages
(games, progression) append their routes below.
"""
from django.urls import path

from . import v1_exhibition_views as views

urlpatterns = [
    path('', views.exhibition_index, name='exhibition_index'),
    path('squat/', views.exhibition_squat, name='exhibition_squat'),
]
