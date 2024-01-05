from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import gettext as _
from django.views.generic import DetailView, View

from spacetraders import Client
from .models import Agent, System, Waypoint, Ship, Market, MarketTradeGood


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
        context["page_title"] = f"System: {system}"
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
        context["page_title"] = f"Waypoint: {waypoint}"
        context["waypoint"] = waypoint
        return context


class ShipDetail(DetailView):
    model = Ship
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ship = self.get_object()
        context["page_title"] = f"Ship: {ship}"
        context["ship"] = ship
        context["nav"] = ship.nav
        return context


class ShipPurchaseCargo(View):

    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        client = Client()
        ship = Ship.objects.get(symbol=self.kwargs.get("symbol"))
        trade_good = request.POST.get("symbol")
        units = int(request.POST.get("units"))
        msg = ship.purchase_cargo(client, trade_good, units)
        if not msg:
            messages.warning(request, "Purchase of {units} units of {trade_good} unsuccessful")
        else:
            messages.success(request, msg)
        # Redirect to the market detail view of the ship.
        return HttpResponseRedirect(ship.nav.waypoint.market.get_absolute_url())


class MarketDetail(DetailView):
    model = Market

    def get_object(self, queryset=None):
        """Return the market object through the linked waypoint symbol.
        """
        if queryset is None:
            queryset = self.get_queryset()

        symbol = self.kwargs.get("symbol")
        queryset = queryset.filter(waypoint__symbol=symbol)

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No Market found matching the query"))

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        market = self.get_object()
        context["page_title"] = f"Market: {market}"
        context["market"] = market
        context["export_goods"] = MarketTradeGood.objects.filter(market=market, type="EXPORT")
        context["import_goods"] = MarketTradeGood.objects.filter(market=market, type="IMPORT")
        context["exchange_goods"] = MarketTradeGood.objects.filter(market=market, type="EXCHANGE")
        context["ships"] = Ship.objects.filter(nav__waypoint=market.waypoint)
        return context
