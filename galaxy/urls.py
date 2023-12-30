from django.urls import path
from .views import SystemView, SystemImageView


urlpatterns = [
    path("system/<int:pk>/", SystemView.as_view(), name="system_image"),
    path("system/<int:pk>/image/", SystemImageView.as_view(), name="system_image"),
]
