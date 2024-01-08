from django.urls import path
from galaxy import views


urlpatterns = [
    path("agent/register/", views.AgentRegister.as_view(), name="agent_register"),
    path("agent/login/", views.AgentLogin.as_view(), name="agent_login"),
    path("agent/<str:symbol>/", views.AgentDetail.as_view(), name="agent_detail"),
    path("ship/<str:symbol>/", views.ShipDetail.as_view(), name="ship_detail"),
    path("ship/<str:symbol>/purchase-cargo/", views.ShipPurchaseCargo.as_view(), name="ship_purchase_cargo"),
    path("ship/<str:symbol>/navigate/", views.ShipNavigate.as_view(), name="ship_navigate"),
    path("ship/<str:symbol>/flight-mode/", views.ShipFlightMode.as_view(), name="ship_flight_mode"),
    path("system/<str:symbol>/", views.SystemDetail.as_view(), name="system_detail"),
    path("waypoint/<str:symbol>/", views.WaypointDetail.as_view(), name="waypoint_detail"),
    path("market/<str:symbol>/", views.MarketDetail.as_view(), name="market_detail"),
    path("", views.HomePage.as_view(), name="home_page",)
]
