from django.views.generic import DetailView

from .models import Agent, System, Waypoint, Ship, Market


class AgentDetail(DetailView):
    model = Agent
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = str(self.get_object())
        context["agent"] = self.get_object()
        return context


class SystemDetail(DetailView):
    model = System
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        system = self.get_object()
        context["page_title"] = str(system)
        context["system_symbol"] = system.symbol
        waypoints = Waypoint.objects.filter(system=system)
        star = waypoints.filter(type="GAS_GIANT").first()

        context["centrex"] = star.x
        context["centrey"] = star.y
        context["waypoints"] = waypoints
        context["minx"] = min([wp.x for wp in waypoints]) - 5
        context["miny"] = min([wp.y for wp in waypoints]) - 5
        context["width"] = max([wp.x for wp in waypoints]) + abs(context["minx"]) + 5
        context["height"] = max([wp.y for wp in waypoints]) + abs(context["miny"]) + 5
        context["ships"] = Ship.objects.filter(nav__waypoint__system=system)
        context["markets"] = Market.objects.filter(waypoint__system=system)
        context["asteroid_waypoints"] = ["ASTEROID", "ASTEROID_BASE", "ASTEROID_FIELD", "ENGINEERED_ASTEROID"]

        return context


class WaypointDetail(DetailView):
    model = Waypoint
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        waypoint = self.get_object()
        context["page_title"] = str(waypoint)
        context["waypoint"] = waypoint
        return context


class ShipDetail(DetailView):
    model = Ship
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ship = self.get_object()
        context["page_title"] = str(ship)
        context["ship"] = ship
        context["nav"] = ship.nav
        return context
