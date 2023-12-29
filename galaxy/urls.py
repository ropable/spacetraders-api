from django.urls import path
from .views import SystemImageView


urlpatterns = [
    path("system/<int:pk>/", SystemImageView.as_view(), name="system_image"),
]
