from django.urls import path
from galaxy import views


urlpatterns = [
    path("agent/<int:pk>/", views.AgentDetail.as_view(), name="agent_detail"),
    path("system/<int:pk>/", views.SystemDetail.as_view(), name="system_detail"),
    path("waypoint/<int:pk>/", views.WaypointDetail.as_view(), name="waypoint_detail"),
    path("ship/<int:pk>/", views.ShipDetail.as_view(), name="ship_detail"),
]
