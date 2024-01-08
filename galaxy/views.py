from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import TemplateView, DetailView, View

from spacetraders import Client
from .models import (
    Faction,
    Agent,
    System,
    Waypoint,
    Ship,
    Market,
    MarketTradeGood,
)


class HomePage(TemplateView):
    template_name = "galaxy/home_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "SpaceTraders"
        context["factions"] = Faction.objects.all()
        return context

    def get(self, request, *args, **kwargs):
        # If the user is already authenticated, redrect to the Agent detail view.
        if request.user.is_authenticated:
            agent = request.user.agent
            return HttpResponseRedirect(reverse("agent_detail", kwargs={"symbol": agent.symbol}))
        return super().get(request, *args, **kwargs)


class AgentRegister(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        symbol = request.POST.get("symbol")
        faction = request.POST.get("faction")
        return HttpResponse(f"You want to register {symbol} as a member of {faction}")


class AgentLogin(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        # If the user is already authenticated, redrect to the Agent detail view.
        if request.user.is_authenticated:
            agent = request.user.agent
            return HttpResponseRedirect(reverse("agent_detail", kwargs={"symbol": agent.symbol}))

        token = request.POST.get("token")
        client = Client(token=token)

        try:
            data = client.get_agent()
        except:
            # Invalid bearer token
            messages.warning(request, "Invalid / expired bearer token")
            return HttpResponseRedirect(reverse("home_page"))

        if not Agent.objects.filter(account_id=data["accountId"]).exists():
            agent = Agent.objects.create(
                account_id=data["accountId"],
                symbol=data["symbol"],
            )
            # TODO: properly bootstrap a new agent/user into the database:
            #  - Starting system
            #  - Ships
        else:
            agent = Agent.objects.get(account_id=data["accountId"])

        starting_faction = Faction.objects.get(symbol=data["startingFaction"])
        agent.starting_faction = starting_faction
        agent.credits = data["credits"]
        agent.ship_count = data["shipCount"]
        agent.save()

        User = get_user_model()
        queryset = User.objects.filter(agent=agent)

        if not queryset.exists():
            user = User.objects.create_user(agent.symbol.lower())
            agent.user = user
            agent.save()
        else:
            user = queryset.get()

        login(request, user)
        return HttpResponseRedirect(reverse("agent_detail", kwargs={"symbol": user.agent.symbol}))


@method_decorator(login_required, name="dispatch")
class AgentDetail(DetailView):
    model = Agent
    slug_field = "symbol"
    slug_url_kwarg = "symbol"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = str(self.get_object())
        context["agent"] = self.get_object()
        return context


@method_decorator(login_required, name="dispatch")
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


@method_decorator(login_required, name="dispatch")
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


@method_decorator(login_required, name="dispatch")
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


@method_decorator(login_required, name="dispatch")
class ShipPurchaseCargo(View):
    """POST-only view to allow a ship to purchase cargo."""
    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        client = Client()
        ship = Ship.objects.get(symbol=self.kwargs.get("symbol"))
        trade_good = request.POST.get("symbol")
        units = int(request.POST.get("units"))
        msg = ship.purchase_cargo(client, trade_good, units)
        if not msg:
            messages.warning(request, f"Purchase of {units} units of {trade_good} unsuccessful")
        else:
            messages.success(request, msg)
        return HttpResponseRedirect(request.POST.get("next"))


@method_decorator(login_required, name="dispatch")
class ShipNavigate(View):
    """POST-only view to allow a ship to navigate to another waypoint."""
    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        client = Client()
        ship = Ship.objects.get(symbol=self.kwargs.get("symbol"))
        waypoint = request.POST.get("waypoint")

        msg = ship.navigate(client, waypoint)
        if not msg:
            messages.warning(request, f"{ship} navigation to {waypoint} unsuccessful")
        else:
            messages.success(request, msg)
        return HttpResponseRedirect(request.POST.get("next"))


@method_decorator(login_required, name="dispatch")
class ShipFlightMode(View):
    """POST-only view to allow a ship to navigate to another waypoint."""
    http_method_names = ["post"]

    def post(self, request, *args, **kargs):
        client = Client()
        ship = Ship.objects.get(symbol=self.kwargs.get("symbol"))
        mode = request.POST.get("mode")
        msg = ship.flight_mode(client, mode)
        messages.success(request, msg)
        return HttpResponseRedirect(request.POST.get("next"))


@method_decorator(login_required, name="dispatch")
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
