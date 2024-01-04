from django.urls import path
from galaxy import views


urlpatterns = [
    path("agent/<str:symbol>/", views.AgentDetail.as_view(), name="agent_detail"),
    path("ship/<str:symbol>/", views.ShipDetail.as_view(), name="ship_detail"),
    path("system/<str:symbol>/", views.SystemDetail.as_view(), name="system_detail"),
    path("waypoint/<str:symbol>/", views.WaypointDetail.as_view(), name="waypoint_detail"),
    path("market/<str:symbol>/", views.MarketDetail.as_view(), name="market_detail"),
]
