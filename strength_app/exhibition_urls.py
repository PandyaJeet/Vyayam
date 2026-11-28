"""Stall pages, mounted at /exhibition/ (vyayam_project/urls.py).

Every view here 404s unless settings.EXHIBITION_MODE. Later stall pages
(games, progression, bicep-curl) append their routes below.
"""
from django.urls import path

from . import v1_exhibition_progression as progression
from . import v1_exhibition_views as views

urlpatterns = [
    path('', views.exhibition_index, name='exhibition_index'),
    path('games/', views.exhibition_games, name='exhibition_games'),
    path('squat/', views.exhibition_squat, name='exhibition_squat'),
    path('bicep-curl/', views.exhibition_bicep_curl, name='exhibition_bicep_curl'),
    path('progression/', progression.exhibition_progression, name='exhibition_progression'),
]
