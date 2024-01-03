from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.contrib.admin import display
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from django_rq.queues import get_queue
from humanize import naturaldelta
import logging
from math import dist
import random
from time import sleep
from zoneinfo import ZoneInfo

TZ = ZoneInfo(settings.TIME_ZONE)
LOGGER = logging.getLogger("spacetraders")


class FactionTrait(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Faction(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    headquarters = models.ForeignKey("System", on_delete=models.PROTECT, null=True, blank=True)
    traits = models.ManyToManyField(FactionTrait, blank=True)
    is_recruiting = models.BooleanField(default=False)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Agent(models.Model):
    modified = models.DateTimeField(auto_now=True)
    account_id = models.CharField(max_length=64, unique=True)
    symbol = models.CharField(max_length=32, unique=True)
    email = models.EmailField(max_length=256, null=True, blank=True)
    starting_faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    headquarters = models.ForeignKey("Waypoint", on_delete=models.PROTECT, null=True, blank=True)
    credits = models.IntegerField(default=0)
    ship_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.symbol} ({self.starting_faction})"

    def get_absolute_url(self):
        return reverse("agent_detail", kwargs={"pk": self.pk})

    def update(self, data):
        """Update object from passed-in data."""
        self.credits = data["credits"]
        self.ship_count = data["shipCount"]
        self.save()

    def refresh(self, client):
        data = client.get_agent()
        self.update(data)
        LOGGER.info(f"Refreshed data for {self}")


class System(models.Model):
    TYPE_CHOICES = (
        ("NEUTRON_STAR", "neutron star"),
        ("RED_STAR", "red star"),
        ("ORANGE_STAR", "orange star"),
        ("BLUE_STAR", "blue star"),
        ("YOUNG_STAR", "young star"),
        ("WHITE_DWARF", "white dwarf"),
        ("BLACK_HOLE", "black hole"),
        ("HYPERGIANT", "hypergiant"),
        ("NEBULA", "nebula"),
        ("UNSTABLE", "unstable"),
    )
    symbol = models.CharField(max_length=32, unique=True)
    sector = models.CharField(max_length=32)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, db_index=True)
    x = models.IntegerField(editable=False)
    y = models.IntegerField(editable=False)
    factions = models.ManyToManyField(Faction, blank=True)

    class Meta:
        ordering = ("sector", "symbol")
        unique_together = ("symbol", "sector")

    def __str__(self):
        return f"{self.symbol} ({self.get_type_display()})"

    def get_absolute_url(self):
        return reverse("system_detail", kwargs={"pk": self.pk})

    @property
    def coords(self):
        return (self.x, self.y)


class WaypointTrait(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class WaypointModifier(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Waypoint(models.Model):
    TYPE_CHOICES = (
        ("PLANET", "planet"),
        ("GAS_GIANT", "gas giant"),
        ("MOON", "moon"),
        ("ORBITAL_STATION", "orbital station"),
        ("JUMP_GATE", "jump gate"),
        ("ASTEROID_FIELD", "asteroid field"),
        ("ASTEROID", "asteroid"),
        ("ENGINEERED_ASTEROID", "engineered asteroid"),
        ("ASTEROID_BASE", "asteroid base"),
        ("NEBULA", "nebula"),
        ("DEBRIS_FIELD", "debris field"),
        ("GRAVITY_WELL", "gravity well"),
        ("ARTIFICIAL_GRAVITY_WELL", "artificial gravity well"),
        ("FUEL_STATION", "fuel station"),
    )
    modified = models.DateTimeField(auto_now=True)
    symbol = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, db_index=True)
    system = models.ForeignKey(
        System, related_name="waypoints", on_delete=models.PROTECT, null=True, blank=True)
    x = models.IntegerField(editable=False)
    y = models.IntegerField(editable=False)
    orbits = models.ForeignKey(
        "self", related_name="orbitals", on_delete=models.PROTECT, null=True, blank=True)
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    traits = models.ManyToManyField(WaypointTrait, blank=True)
    modifiers = models.ManyToManyField(WaypointModifier, blank=True)
    is_under_construction = models.BooleanField(default=False)

    class Meta:
        ordering = ("symbol",)
        unique_together = ("symbol", "system")

    def __str__(self):
        return f"{self.symbol} ({self.get_type_display()})"

    def get_absolute_url(self):
        return reverse("waypoint_detail", kwargs={"pk": self.pk})

    def update(self, data):
        """Update object from passed-in data."""
        if "orbits" in data and data["orbits"]:
            self.orbits = Waypoint.objects.get(symbol=data["orbits"])
        if data["orbitals"]:
            for orbital in data["orbitals"]:
                waypoint = Waypoint.objects.get(symbol=orbital["symbol"])
                waypoint.orbits = self
                waypoint.save()
        if data["traits"]:
            for trait in data["traits"]:
                self.traits.add(WaypointTrait.objects.get(symbol=trait["symbol"]))
        if data["modifiers"]:
            for mod in data["modifers"]:
                self.modifiers.add(WaypointModifier.objects.get(symbol=mod["symbol"]))
        if data["faction"]:
            self.faction = Faction.objects.get(symbol=data["faction"]["symbol"])
        if data["chart"]:
            chart, created = Chart.objects.get_or_create(
                waypoint=self,
                submitted_by=Faction.objects.get(symbol=data["chart"]["submittedBy"]),
                submitted_on=data["chart"]["submittedOn"],
            )
            self.chart = chart
        self.is_under_construction = data["isUnderConstruction"]

        self.save()

    def refresh(self, client):
        data = client.get_waypoint(self.symbol)
        self.update(data)

        if self.is_market:
            data = client.get_market(self.symbol)
            self.market.update(data)

        if self.is_shipyard:
            data = client.get_shipyard(self.symbol)
            self.shipyard.update(data)
        # TODO: jump gate

        msg = f"{self} data updated"
        LOGGER.info(msg)
        return msg

    @property
    @display(description="suffix")
    def symbol_suffix(self):
        return self.symbol.split("-")[-1]

    @property
    @display(description="orbitals")
    def orbitals_display(self):
        return ", ".join([str(o) for o in self.orbitals.all()])

    @property
    def coords(self):
        return (self.x, self.y)

    @property
    def is_market(self):
        return self.has_trait("MARKETPLACE")

    @property
    def is_shipyard(self):
        return self.has_trait("SHIPYARD")

    def has_trait(self, trait):
        if WaypointTrait.objects.filter(symbol=trait).exists() and WaypointTrait.objects.get(symbol=trait) in self.traits.all():
            return True
        else:
            return False

    def distance(self, coords):
        if not isinstance(coords, tuple):
            return False
        return dist((self.x, self.y), (coords[0], coords[1]))

    def traits_display(self):
        if self.traits:
            return ", ".join([t.name for t in self.traits.all()])
        else:
            return ""

    def get_export_markets(self):
        """For a given market waypoint, return a list of other exporter waypoints in the same system sorted by distance.
        Returns [(<Waypoint>, <distance>), ...]
        """
        export_markets = Market.objects.filter(exports__isnull=False, waypoint__system=self.system).distinct()
        export_waypoints = [(e.waypoint, e.waypoint.distance(self.coords), e.exports_display) for e in export_markets]
        export_waypoints = sorted(export_waypoints, key=lambda x: x[1])
        return export_waypoints


class Chart(models.Model):
    waypoint = models.ForeignKey(Waypoint, on_delete=models.CASCADE, null=True, blank=True)
    submitted_by = models.CharField(max_length=32)
    submitted_on = models.DateTimeField()


class ShipNav(models.Model):
    STATUS_CHOICES = (
        ("IN_TRANSIT", "in transit"),
        ("IN_ORBIT", "in orbit"),
        ("DOCKED", "docked"),
    )
    FLIGHT_MODE_CHOICES = (
        ("DRIFT", "drift"),
        ("STEALTH", "stealth"),
        ("CRUISE", "cruise"),
        ("BURN", "burn"),
    )
    modified = models.DateTimeField(auto_now=True)
    system = models.ForeignKey(System, related_name="shipnavs", on_delete=models.PROTECT, null=True, blank=True)
    waypoint = models.ForeignKey(Waypoint, related_name="shipnavs", on_delete=models.PROTECT, null=True, blank=True)
    route = models.JSONField(default=dict)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    flight_mode = models.CharField(max_length=32, choices=FLIGHT_MODE_CHOICES)

    def __str__(self):
        if self.status in ["DOCKED", "IN_ORBIT"]:
            return f"{self.get_status_display()} at {self.waypoint}, {self.get_flight_mode_display()} mode"
        else:
            return f"{self.get_status_display()} to {self.waypoint}, {self.get_flight_mode_display()} mode ({self.route['arrival']})"

    @property
    def is_in_transit(self):
        return self.status == "IN_TRANSIT"

    def update(self, data):
        """Update from passed-in nav data."""
        self.system = System.objects.get(symbol=data["systemSymbol"])
        self.waypoint = Waypoint.objects.get(symbol=data["waypointSymbol"])
        self.route = data["route"]
        self.status = data["status"]
        self.flight_mode = data["flightMode"]
        self.save()

    def get_arrival(self):
        """Returns route.arrival as a datetime."""
        if "arrival" in self.route:
            return datetime.fromisoformat(self.route["arrival"])
        return None

    def arrival_display(self):
        """Returns a human-readable string for the arrival time of a ship in transit."""
        arrival = self.get_arrival()
        if arrival:
            now = datetime.now(timezone.utc)
            if arrival < now:
                return f"in the past ({arrival.astimezone(TZ).strftime('%d-%b-%Y %H:%M:%S')})"
            return f"{naturaldelta(arrival - now)} ({arrival.astimezone(TZ).strftime('%d-%b-%Y %H:%M:%S')})"
        else:
            return ""

    def get_fuel_cost(self, coords):
        """For the passed-in coordinates, calculate the travel fuel cost based on the distance and
        flight mode.
        Reference: https://github.com/SpaceTradersAPI/api-docs/wiki/Travel-Fuel-and-Time
        """
        distance = self.waypoint.distance(coords)
        if self.flight_mode in ["CRUISE", "STEALTH"]:
            return int(distance)
        elif self.flight_mode == "BURN":
            return int(distance) * 2
        elif self.flight_mode == "DRIFT":
            return 1

        return

    def get_navigate_time(self, distance):
        """For the passed-in distance, calculate the navigate travel time in seconds.
        Reference: https://github.com/SpaceTradersAPI/api-docs/wiki/Travel-Fuel-and-Time
        """
        distance = int(distance)
        if distance <= 0:
            return

        if self.flight_mode == "CRUISE":
            nav_multiplier = 25.0
        elif self.flight_mode == "DRIFT":
            nav_multiplier = 250.0
        elif self.flight_mode == "BURN":
            nav_multiplier = 12.5
        elif self.flight_mode == "STEALTH":
            nav_multiplier = 30.0
        else:
            return

        return round(max(1, distance) * (nav_multiplier / self.ship.engine["speed"]) + 15)


class ShipModule(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    range = models.PositiveIntegerField(default=0)
    requirements = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class ShipMount(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    strength = models.PositiveIntegerField(default=0)
    deposits = ArrayField(base_field=models.CharField(max_length=32), blank=True, null=True)
    requirements = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Ship(models.Model):
    modified = models.DateTimeField(auto_now=True)
    agent = models.ForeignKey(Agent, related_name="ships", on_delete=models.PROTECT)
    symbol = models.CharField(max_length=32, unique=True)
    registration = models.JSONField(default=dict)
    nav = models.OneToOneField(ShipNav, on_delete=models.CASCADE)
    crew = models.JSONField(default=dict)
    frame = models.JSONField(default=dict)
    reactor = models.JSONField(default=dict)
    engine = models.JSONField(default=dict)
    cooldown = models.JSONField(default=dict)
    modules = models.ManyToManyField(ShipModule, blank=True)
    mounts = models.ManyToManyField(ShipMount, blank=True)
    cargo_capacity = models.PositiveIntegerField(default=0)
    cargo_units = models.PositiveIntegerField(default=0)
    fuel = models.JSONField(default=dict)

    # Non-API (local) fields.
    BEHAVIOUR_CHOICES = (
        (None, "None"),
        ("TRADE", "Trading"),
        ("MINE", "Mining"),
        ("HAUL", "Hauling"),
    )
    behaviour = models.CharField(
        max_length=32,
        choices=BEHAVIOUR_CHOICES,
        blank=True,
        null=True,
        help_text="Desired autonomous behaviour",
    )

    class Meta:
        ordering = ("symbol",)
        unique_together = ("agent", "symbol")

    def __str__(self):
        return f"{self.symbol} ({self.frame['name']})"

    def get_absolute_url(self):
        return reverse("ship_detail", kwargs={"pk": self.pk})

    @property
    @display(description="frame")
    def frame_name(self):
        return self.frame["name"]

    @property
    def is_docked(self):
        return self.nav.status == "DOCKED"

    @property
    def is_in_orbit(self):
        return self.nav.status == "IN_ORBIT"

    @property
    def is_in_cooldown(self):
        cooldown = self.get_cooldown()
        now = datetime.now(timezone.utc)
        if cooldown and cooldown >= now:
            return True
        else:
            return False

    @property
    def role(self):
        return self.registration["role"].capitalize()

    @property
    @display(description="mounts")
    def mounts_display(self):
        return ', '.join([str(mount) for mount in self.mounts.all()])

    @property
    @display(description="modules")
    def modules_display(self):
        return ', '.join([str(module) for module in self.modules.all()])

    def orbit(self, client):
        if not self.is_docked:
            return

        data = client.orbit_ship(self.symbol)
        self.nav.update(data["nav"])
        msg = f"{self} entered orbit at {self.nav.waypoint.symbol}"
        LOGGER.info(msg)
        return msg

    def dock(self, client):
        if not self.is_in_orbit:
            return

        data = client.dock_ship(self.symbol)
        self.nav.update(data["nav"])
        msg = f"{self} docked at {self.nav.waypoint.symbol}"
        LOGGER.info(msg)
        return msg

    def flight_mode(self, client, mode: str):
        """Set the flight mode for this ship."""
        if mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = client.ship_flight_mode(self.symbol, mode)
        # Update ship.nav
        self.nav.update(data)

        msg = f"{self} flight mode set to {mode}"
        LOGGER.info(msg)
        return msg

    def navigate(self, client, waypoint_symbol: str):
        """Navigate this ship to the nominated waypoint.
        """
        if not self.is_in_orbit:
            self.orbit(client)

        # Determine if the destination waypoint is in range using the preset flight mode.
        # If not, set it to DRIFT mode.
        destination = Waypoint.objects.get(symbol=waypoint_symbol)
        if self.nav.get_fuel_cost(destination.coords) >= self.fuel["current"]:
            self.flight_mode(client, "DRIFT")

        data = client.navigate_ship(self.symbol, waypoint_symbol)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        # data contains: fuel, nav
        self.fuel = data["fuel"]
        self.save()

        # Update ship.nav
        self.nav.update(data["nav"])

        # Queue a refresh of this ship's data on arrival.
        queue = get_queue("default")
        queue.enqueue_at(self.nav.get_arrival(), self.refresh, client)
        msg = f"{self} en route to {self.nav.route['destination']['symbol']} ({self.nav.flight_mode}), arrival in {self.nav.arrival_display()}"
        LOGGER.info(msg)
        return msg

    def refuel(self, client, units: int = None, from_cargo: bool = False):
        if not self.is_docked:
            self.dock(client)
            self.refresh(client)

        data = client.refuel_ship(self.symbol, units, from_cargo)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        # data contains: agent, fuel, transaction
        self.fuel = data["fuel"]
        self.save()

        # Update agent.
        self.agent.update(data["agent"])

        # Create a transaction for the fuel purchase.
        market = Market.objects.get(waypoint__symbol=data["transaction"]["waypointSymbol"])
        Transaction.objects.create(
            market=market,
            ship_symbol=data["transaction"]["shipSymbol"],
            trade_good=TradeGood.objects.get(symbol="FUEL"),
            type=data["transaction"]["type"],
            units=data["transaction"]["units"],
            price_per_unit=data["transaction"]["pricePerUnit"],
            total_price=data["transaction"]["totalPrice"],
            timestamp=data["transaction"]["timestamp"],
        )

        msg = f"{self} refueled {data['transaction']['units']} units"
        LOGGER.info(msg)
        return msg

    def update(self, data):
        """Update ship details from passed-in ship data.
        Note that we update cargo in a separate method.
        """
        self.crew = data["crew"]
        self.frame = data["frame"]
        self.reactor = data["reactor"]
        self.engine = data["engine"]
        self.cooldown = data["cooldown"]
        self.fuel = data["fuel"]
        self.save()

        # Update ship.nav
        self.nav.update(data["nav"])

        # Update modules
        self.modules.clear()
        for module_data in data["modules"]:
            if not ShipModule.objects.filter(symbol=module_data["symbol"]).exists():
                module = ShipModule(
                    symbol=module_data["symbol"],
                    name=module_data["name"],
                    description=module_data["description"],
                )
                if "capacity" in module_data:
                    module.capacity = module_data["capacity"]
                if "range" in module_data:
                    module.range = module_data["range"]
                if "requirements" in module_data:
                    module.requirements = module_data["requirements"]
                module.save()
            else:
                module = ShipModule.objects.get(symbol=module_data["symbol"])
            self.modules.add(module)

        # Update mounts
        self.mounts.clear()
        for mount_data in data["mounts"]:
            if not ShipMount.objects.filter(symbol=mount_data["symbol"]).exists():
                mount = ShipMount(
                    symbol=mount_data["symbol"],
                    name=mount_data["name"],
                    description=mount_data["description"],
                )
                if "strength" in mount_data:
                    mount.strength = mount_data["strength"]
                if "deposits" in mount_data:
                    mount.deposits = mount_data["deposits"]
                if "requirements" in mount_data:
                    mount.requirements = mount_data["requirements"]
                mount.save()
            else:
                mount = ShipMount.objects.get(symbol=mount_data["symbol"])
            self.mounts.add(mount)

        #LOGGER.info(f"{self} updated")

    def update_cargo(self, data):
        """Update ship cargo from passed-in data.
        """
        self.cargo_capacity = data["capacity"]
        self.cargo_units = data["units"]
        self.save()

        # If the ship's cargo inventory is empty, clear it.
        if not data["inventory"]:
            ShipCargoItem.objects.filter(ship=self).delete()
        else:
            for good in data["inventory"]:
                if not CargoType.objects.filter(symbol=good["symbol"]).exists():
                    cargo_type = CargoType.objects.create(
                        symbol=good["symbol"],
                        name=good["name"],
                        description=good["description"],
                    )
                else:
                    cargo_type = CargoType.objects.get(symbol=good["symbol"])

                # New inventory good.
                if not ShipCargoItem.objects.filter(type=cargo_type, ship=self).exists():
                    item = ShipCargoItem.objects.create(
                        type=cargo_type,
                        ship=self,
                        units=good["units"],
                    )
                elif ShipCargoItem.objects.filter(type=cargo_type, ship=self).exists():
                    # Update the number of units if required.
                    item = ShipCargoItem.objects.get(type=cargo_type, ship=self)
                    if item.units != good["units"]:
                        item.units = good["units"]
                        item.save()

                # Check the set of ship cargo items. If there is anything not currently in inventory,
                # delete any of those ShipCargoItem objects.
                current_cargo = CargoType.objects.filter(symbol__in=[good["symbol"] for good in data["inventory"]])
                ShipCargoItem.objects.filter(ship=self).exclude(type__in=current_cargo).delete()

        #LOGGER.info(f"{self} cargo updated")

    def purchase_cargo(self, client, trade_good: str, units: int = None):
        if not self.is_docked:
            self.dock(client)
            self.refresh(client)

        # If units is not supplied, purchase the largest amount available.
        if not units:
            market = self.nav.waypoint.market
            market_trade_good = MarketTradeGood.objects.get(market=market, trade_good=TradeGood.objects.get(symbol=trade_good))
            available_capacity = self.cargo_capacity - self.cargo_units
            # If the available volume on the market is less than our ship's available capacity, use that.
            if market_trade_good.trade_volume < available_capacity:
                units = market_trade_good.trade_volume
            else:
                units = available_capacity

        data = client.purchase_cargo(self.symbol, trade_good, units)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        # data contains: agent, cargo, transaction
        self.update_cargo(data["cargo"])
        # Update agent.
        self.agent.update(data["agent"])
        # Create a transaction
        market = Market.objects.get(waypoint__symbol=data["transaction"]["waypointSymbol"])
        trade_good = TradeGood.objects.get(symbol=data["transaction"]["tradeSymbol"])
        transaction = Transaction.objects.create(
            market=market,
            ship_symbol=data["transaction"]["shipSymbol"],
            trade_good=trade_good,
            type=data["transaction"]["type"],
            units=data["transaction"]["units"],
            price_per_unit=data["transaction"]["pricePerUnit"],
            total_price=data["transaction"]["totalPrice"],
            timestamp=data["transaction"]["timestamp"],
        )
        # Update the local market conditions.
        self.nav.waypoint.refresh(client)

        msg = f"{self} purchased {transaction.units} units of {trade_good} for {transaction.total_price}"
        LOGGER.info(msg)
        return msg

    def purchase_ship(self, client, ship_type: str):
        """Purchase a ship of the given type at the current waypoint.
        """
        if not self.is_docked:
            self.dock(client)
            self.refresh(client)

        data = client.purchase_ship(self.nav.waypoint.symbol, ship_type)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        # Populate the new ship in the database.
        from .utils import populate_ship
        ship = populate_ship(client, self.agent, data["ship"])
        # Update agent.
        self.agent.update(data["agent"])
        msg = f"Purchased {ship}"
        LOGGER.info(msg)
        return msg

    def sell_cargo(self, client):
        """Convenience function to try selling all the ship's cargo at the current waypoint.
        """
        if not self.is_docked:
            self.dock(client)
            self.refresh(client)

        transactions = []
        for cargo in self.cargo.all():
            LOGGER.info(f"Selling {cargo}")
            result = cargo.sell(client)
            if not result:
                LOGGER.warning(f"Error during sell for {cargo}")
                return False
            else:
                transactions.append(result)

        # Update the local market conditions.
        self.nav.waypoint.refresh(client)
        return transactions

    def refresh(self, client):
        data = client.get_ship(self.symbol)
        self.update(data)
        self.update_cargo(data["cargo"])

        msg = f"{self} data updated"
        LOGGER.info(msg)
        return msg

    def find_destination(self, trait=None, type=None):
        """Return a list of waypoints having the nominated trait, ordered by distance from this ship.
        """
        if not trait and not type:
            return

        waypoints = Waypoint.objects.all()

        if trait:
            try:
                waypoint_trait = WaypointTrait.objects.get(symbol=trait)
                waypoints = waypoints.filter(traits__in=[waypoint_trait])
            except:
                return False
        if type:
            try:
                waypoints = waypoints.filter(type=type)
            except:
                return False

        origin = self.nav.waypoint.coords
        destinations = []
        for wp in waypoints:
            destinations.append((wp.distance(origin), wp))

        destinations = sorted(destinations, key=lambda x: x[0])
        return destinations

    def sleep_until_arrival(self):
        """Sleep (blocking) until the scheduled arrival time for this ship.
        """
        now = datetime.now(timezone.utc)
        arrival = datetime.fromisoformat(self.nav.route["arrival"])
        if arrival < now:
            return
        pause = (arrival - now).seconds + 1
        print(f"Sleeping {self.nav.arrival_display()}")
        sleep(pause)

    def get_cooldown(self):
        """Returns ship cooldown as a datetime, or None."""
        if "expiration" in self.cooldown:
            return datetime.fromisoformat(self.cooldown["expiration"])
        return None

    def cooldown_display(self):
        """Returns a human-readable string for the cooldown time of the ship."""
        cooldown = self.get_cooldown()
        if cooldown:
            now = datetime.now(timezone.utc)
            if cooldown < now:
                return f"in the past ({cooldown.astimezone(TZ).strftime('%d-%b-%Y %H:%M:%S')})"
            return f"{naturaldelta(cooldown - now)} ({cooldown.astimezone(TZ).strftime('%d-%b-%Y %H:%M:%S')})"
        else:
            return ""

    def sleep_until_cooldown(self):
        """Sleep (blocking) until the cooldown period ends for this ship.
        """
        now = datetime.now(timezone.utc)
        cooldown = datetime.fromisoformat(self.cooldown["expiration"])
        if cooldown < now:
            return
        pause = (cooldown - now).seconds
        print(f"Sleeping for {self.nav.cooldown_display()}")
        sleep(pause)

    def siphon(self, client):
        """Extract gas resources from a waypoint."""
        if not self.is_in_orbit:
            self.orbit(client)
        if self.is_in_cooldown:
            msg = f"{self} is currently in cooldown for {self.cooldown_display()}"
            LOGGER.info(msg)
            return msg

        data = client.siphon_resources(self.symbol)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        self.cooldown = data["cooldown"]
        self.save()
        self.update_cargo(data["cargo"])
        siphon_yield = data["siphon"]["yield"]
        msg = f"{self} siphon yielded {siphon_yield['units']} {siphon_yield['symbol']}"
        LOGGER.info(msg)
        return msg

    def extract(self, client, survey=None):
        """Extract resources from a waypoint.
        TODO: make use of an optional survey object.
        """
        if not self.is_in_orbit:
            self.orbit(client)
        if self.is_in_cooldown:
            msg = f"{self} is currently in cooldown for {self.cooldown_display()}"
            LOGGER.info(msg)
            return msg

        data = client.extract_resources(self.symbol)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        self.cooldown = data["cooldown"]
        self.save()
        self.update_cargo(data["cargo"])
        extract_yield = data["extraction"]["yield"]
        msg = f"{self} extract yielded {extract_yield['units']} {extract_yield['symbol']}"
        LOGGER.info(msg)
        return msg

    def extract_until_full(self, client, target_resource: str = None):
        """If the ship's cargo capacity is not full, queue an extract action for after the
        cooldown or immediately (whichever is soonest).
        """
        if self.cargo_units < self.cargo_capacity:
            self.extract(client)

        # Optional step: jettison any cargo that isn't the target_resource
        if target_resource:
            cargo_type = CargoType.objects.get(symbol=target_resource)
            for cargo in self.cargo.all().exclude(type=cargo_type):
                cargo.jettison(client)

        # Queue the next extraction, if required.
        if self.cargo_units < self.cargo_capacity:
            msg = f"{self} queued extract in {self.cooldown_display()}"
            LOGGER.info(msg)
            queue = get_queue("default")
            queue.enqueue_at(self.get_cooldown(), self.extract_until_full, client, target_resource)
            return msg

        # Ship is full, cease queuing actions.
        msg = f"{self} cargo is full, ceasing extraction"
        LOGGER.info(msg)
        return msg

    def get_export_markets(self):
        """Returns the list of market waypoints having exports, sorted nearest > furtherest from this ship.
        """
        return self.nav.waypoint.get_export_markets()

    def trade_workflow(self, client, trade_good: str, destination_symbol: str, units: int = None):
        """Carry out an automated trade workflow for this ship.
        Purchase the passed-in trade good, navigate to the destination waypoint, and sell the cargo.
        """
        self.purchase_cargo(client, trade_good, units)
        self.navigate(client, destination_symbol)
        # Steps below are queued for after arrival.
        queue = get_queue("default")
        arrival = self.nav.get_arrival()
        # Sell the cargo
        queue.enqueue_at(arrival, self.sell_cargo, client)
        # Refuel the ship
        queue.enqueue_at(arrival + timedelta(seconds=5), self.refuel, client)

    def behaviour_trade(self, client):
        """Carry out 'trade randomly, forever' behaviour.
        Options:
            - Sell cargo at the current location.
            - Navigate elsewhere to an export market.
            - Purchase cargo and navigate to the destination import market.
        """
        if not self.behaviour == "TRADE":
            return  # Abort
        else:
            LOGGER.info(f"{self} behaviour is TRADE")

        # Refresh ship data.
        self.refresh(client)
        # Reset flight mode to CRUISE.
        self.flight_mode(client, "CRUISE")
        # Dock & refuel the ship.
        self.dock(client)
        result = self.refuel(client)
        if not result:
            LOGGER.warning("Error during refuel, aborting")
            return

        queue = get_queue("default")

        if self.cargo.exists():
            LOGGER.info(f"{self} selling cargo at the current market")
            # Sell the cargo
            result = self.sell_cargo(client)
            if not result:
                LOGGER.warning("Error during sell_cargo, aborting")
                return
            # Queue up next trade attempt.
            queue.enqueue(self.behaviour_trade, client)
        elif not self.nav.waypoint.market.get_best_export():
            # Navigate to a random export market.
            export_market_choices = self.get_export_markets()
            destination = random.choice(export_market_choices[0:10])[0]
            LOGGER.info(f"{self} navigating elsewhere to export market ({destination.symbol})")
            result = self.navigate(client, destination.symbol)
            if not result:
                LOGGER.warning("Error during navigate, aborting")
                return
            # Steps below are queued for after arrival.
            arrival = self.nav.get_arrival()
            queue.enqueue_at(arrival + timedelta(seconds=10), self.behaviour_trade, client)
        else:
            # Execute a trade from the current location.
            trade_good_symbol, waypoint_symbol, ratio = self.nav.waypoint.market.get_best_export()
            LOGGER.info(f"{self} purchasing {trade_good_symbol} to sell at {waypoint_symbol}")
            result = self.purchase_cargo(client, trade_good_symbol)
            if not result:
                LOGGER.warning("Error during purchase_cargo, aborting")
                return
            result = self.navigate(client, waypoint_symbol)
            if not result:
                LOGGER.warning("Error during navigate, aborting")
                return
            # Queue up next trade attempt.
            arrival = self.nav.get_arrival()
            queue.enqueue_at(arrival + timedelta(seconds=10), self.behaviour_trade, client)


class CargoType(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class ShipCargoItem(models.Model):
    type = models.ForeignKey(CargoType, on_delete=models.PROTECT, null=True, blank=True)
    ship = models.ForeignKey(Ship, related_name="cargo", on_delete=models.CASCADE, null=True, blank=True)
    units = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("type", "ship")

    def __str__(self):
        return f"{self.units} units of {self.type} ({self.ship.symbol})"

    def sell(self, client, units: int = None):
        """Sell this cargo at the ship's current location."""
        if not units:
            units = self.units

        if not self.ship.is_docked:
            self.ship.dock(client)

        data = client.sell_cargo(self.ship.symbol, self.type.symbol, units)
        if "error" in data:
            LOGGER.error(data["error"]["message"])
            return False

        # data contains: agent, cargo, transaction
        self.ship.update_cargo(data["cargo"])
        # Update agent.
        self.ship.agent.update(data["agent"])
        # Create a transaction for the market
        market = Market.objects.get(waypoint__symbol=data["transaction"]["waypointSymbol"])
        trade_good = TradeGood.objects.get(symbol=data["transaction"]["tradeSymbol"])
        transaction = Transaction.objects.create(
            market=market,
            ship_symbol=data["transaction"]["shipSymbol"],
            trade_good=trade_good,
            type=data["transaction"]["type"],
            units=data["transaction"]["units"],
            price_per_unit=data["transaction"]["pricePerUnit"],
            total_price=data["transaction"]["totalPrice"],
            timestamp=data["transaction"]["timestamp"],
        )

        msg = f"Sold {transaction.units} units of {trade_good} for {transaction.total_price}"
        LOGGER.info(msg)
        return msg

    def jettison(self, client, units: int = None):
        """Jettison this cargo. If `units` is not specified, jettison the full amount.
        """
        if not units:
            units = self.units

        data = client.jettison_cargo(self.ship.symbol, self.type.symbol, units)
        self.ship.update_cargo(data["cargo"])
        msg = f"{self.ship} jettisoned {units} units of {self.type}"
        LOGGER.info(msg)
        return msg


class Contract(models.Model):
    TYPE_CHOICES = (
        ("PROCUREMENT", "procurement"),
        ("TRANSPORT", "transport"),
        ("SHUTTLE", "shuttle"),
    )
    modified = models.DateTimeField(auto_now=True)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT)
    contract_id = models.CharField(max_length=64, unique=True)
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    terms_deadline = models.DateTimeField()
    terms_payment = models.JSONField(default=dict)
    accepted = models.BooleanField(default=False)
    fulfilled = models.BooleanField(default=False)
    expiration = models.DateTimeField()
    deadline_to_accept = models.DateTimeField()

    def __str__(self):
        return f"{self.type} ({self.faction})"

    @property
    def required_goods(self):
        return '\n'.join([str(good) for good in self.deliver_goods.all()])

    def accept(self, client):
        data = client.accept_contract(self.contract_id)
        LOGGER.info(f"Contract {self} accepted")
        self.update(data["contract"])

    def update(self, data):
        self.accepted = data["accepted"]
        self.fulfilled = data["fulfilled"]
        #LOGGER.info(f"{self} updated")
        self.save()

    @property
    def expiration_display(self):
        """Returns a human-readable string for the expiration timestamp"""
        now = datetime.now(timezone.utc)
        return f"{naturaldelta(self.expiration - now)} ({self.expiration.astimezone(TZ).strftime('%d-%b-%Y %H:%M:%S')})"


class ContractDeliverGood(models.Model):
    contract = models.ForeignKey(Contract, related_name="deliver_goods", on_delete=models.CASCADE)
    # TODO: replace symbol with a FK to TradeGood.
    symbol = models.CharField(max_length=128)
    destination = models.ForeignKey(Waypoint, on_delete=models.PROTECT)
    units_required = models.PositiveIntegerField(default=0)
    units_fulfilled = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.symbol} to {self.destination} ({self.units_fulfilled}/{self.units_required})"


class TradeGood(models.Model):
    symbol = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField()
    inputs = models.ManyToManyField("self", symmetrical=False, blank=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Market(models.Model):
    waypoint = models.OneToOneField(Waypoint, on_delete=models.PROTECT)
    exports = models.ManyToManyField(TradeGood, related_name="exports", blank=True)
    imports = models.ManyToManyField(TradeGood, related_name="imports", blank=True)
    exchange = models.ManyToManyField(TradeGood, related_name="exchange", blank=True)

    def __str__(self):
        return str(self.waypoint)

    @property
    @display(description="exports")
    def exports_display(self):
        if not self.exports.exists():
            return None
        return ", ".join([exp.name for exp in self.exports.all()])

    @property
    @display(description="imports")
    def imports_display(self):
        if not self.imports.exists():
            return None
        return ", ".join([imp.name for imp in self.imports.all()])

    @property
    @display(description="exchange")
    def exchange_display(self):
        if not self.exchange.exists():
            return None
        return ", ".join([ex.name for ex in self.exchange.all()])

    def update(self, data):
        """Update from passed-in data."""
        for imp in data["imports"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=imp["symbol"],
                name=imp["name"],
                description=imp["description"],
            )
            self.imports.add(trade_good)

        for exp in data["exports"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=exp["symbol"],
                name=exp["name"],
                description=exp["description"],
            )
            self.exports.add(trade_good)

        # For any exports, call save() in order to make any new trade matches.
        for mtg in self.markettradegood_set.filter(type="EXPORT"):
            mtg.save()

        for ex in data["exchange"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=ex["symbol"],
                name=ex["name"],
                description=ex["description"],
            )
            self.exchange.add(trade_good)

        if "transactions" in data:
            for trans in data["transactions"]:
                # FIXME: assumption here is that the TradeGood already exists.
                # Possibly adjust model to allow null name & description field.
                trade_good = TradeGood.objects.get(symbol=trans["tradeSymbol"])
                transaction, created = Transaction.objects.get_or_create(
                    market=self,
                    ship_symbol=trans["shipSymbol"],
                    trade_good=trade_good,
                    type=trans["type"],
                    units=trans["units"],
                    price_per_unit=trans["pricePerUnit"],
                    total_price=trans["totalPrice"],
                    timestamp=trans["timestamp"],
                )

        if "tradeGoods" in data:
            for good in data["tradeGoods"]:
                trade_good = TradeGood.objects.get(symbol=good["symbol"])
                if not MarketTradeGood.objects.filter(market=self, trade_good=trade_good, type=good["type"]).exists():
                    market_trade_good = MarketTradeGood(
                        market=self,
                        trade_good=trade_good,
                        type=good["type"],
                    )
                else:
                    market_trade_good = MarketTradeGood.objects.get(market=self, trade_good=trade_good, type=good["type"])

                market_trade_good.trade_volume = good["tradeVolume"]
                market_trade_good.supply = good["supply"]
                market_trade_good.purchase_price = good["purchasePrice"]
                market_trade_good.sell_price = good["sellPrice"]
                if "activity" in good:  # Type EXCHANGE goods have no activity
                    market_trade_good.activity = good["activity"]
                market_trade_good.save()

        LOGGER.info(f"Market {self} updated")

    def trade_good_data(self):
        """Returns a boolean whether detailed market trade good data is known about this market.
        """
        return MarketTradeGood.objects.filter(market=self).exists()

    def get_arbitrage(self):
        """Get a list of all arbitrage opportunities for exports from this market. Returns:
        {
            "<TRADE GOOD SYMBOL>": [
                (<waypoint symbol>, distance, spread, spread/distance),
                ...
            ],
            ...
        }
        """
        market_arbitrage = {}
        for mtg in self.markettradegood_set.all():
            arbitrage = mtg.get_arbitrage()
            if arbitrage:
                market_arbitrage[mtg.symbol] = arbitrage
        return market_arbitrage

    def get_best_export(self):
        """Given the list of export arbitrage opportunities for this market,
        return the trade with the "best" ratio of spread / distance.
        Returns (<destination waypoint symbol>, <trade good symbol>, <ratio>) or None.
        """
        if not self.exports.exists():
            return None

        market_arbitrage = self.get_arbitrage()
        best_trade = (None, None, 0)
        for symbol, options in market_arbitrage.items():
            if options and options[0][3] > best_trade[2]:
                best_trade = (symbol, options[0][0], options[0][3])

        if best_trade[-1]:  # Trade has a destination waypoint.
            return best_trade
        else:
            return None


class Transaction(models.Model):
    TYPE_CHOICES = (
        ("PURCHASE", "purchase"),
        ("SELL", "sell"),
    )
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    ship_symbol = models.CharField(max_length=32)
    trade_good = models.ForeignKey(TradeGood, on_delete=models.PROTECT)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    units = models.PositiveIntegerField(default=0)
    price_per_unit = models.PositiveIntegerField(default=0)
    total_price = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ("-timestamp",)

    def __str__(self):
        return f"{self.ship_symbol} {self.type.lower()} {self.units} {self.trade_good} for {self.total_price}"


class MarketTradeGood(models.Model):
    TYPE_CHOICES = (
        ("EXPORT", "export"),
        ("IMPORT", "import"),
        ("EXCHANGE", "exchange"),
    )
    SUPPLY_CHOICES = (
        ("SCARCE", "scarce"),
        ("LIMITED", "limited"),
        ("MODERATE", "moderate"),
        ("HIGH", "high"),
        ("ABUNDANT", "abundant"),
    )
    ACTIVITY_CHOICES = (
        ("WEAK", "weak"),
        ("GROWING", "growing"),
        ("STRONG", "strong"),
        ("RESTRICTED", "restricted"),
    )
    modified = models.DateTimeField(auto_now=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    trade_good = models.ForeignKey(TradeGood, on_delete=models.PROTECT)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    trade_volume = models.PositiveIntegerField(default=0)
    supply = models.CharField(max_length=32, choices=SUPPLY_CHOICES)
    activity = models.CharField(max_length=32, choices=ACTIVITY_CHOICES, null=True, blank=True)
    purchase_price = models.PositiveIntegerField(default=0)
    sell_price = models.PositiveIntegerField(default=0)

    trade_matches = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta:
        unique_together = ("market", "trade_good", "type")

    def __str__(self):
        return f"{self.market.waypoint.symbol} - {self.trade_good} ({self.type.lower()})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Add any matching imports to an export instance.
        if self.type == "EXPORT":
            for good in MarketTradeGood.objects.filter(trade_good=self.trade_good, type="IMPORT"):
                self.trade_matches.add(good)

    @property
    @display(description="waypoint")
    def waypoint_display(self):
        return str(self.market.waypoint)

    @property
    def symbol(self):
        return self.trade_good.symbol

    def get_purchasers(self):
        """Return the list of purchasers for an export trade good.
        """
        if self.type == "EXPORT":
            purchasers = MarketTradeGood.objects.filter(type="IMPORT", trade_good=self.trade_good)
            return [d.market for d in purchasers]
        else:
            return None

    def get_suppliers(self):
        """Return the list of suppliers for an import trade good.
        """
        if self.type == "IMPORT":
            suppliers = MarketTradeGood.objects.filter(type="EXPORT", trade_good=self.trade_good)
            return [d.market for d in suppliers]
        else:
            return None

    def get_arbitrage(self):
        """For an export trade good, return the list of purchase market waypoints, distance, spread
        and spread/distance ratio.
        """
        if self.type == "EXPORT":
            arbitrage = []
            for match in self.trade_matches.all():
                distance = int(match.market.waypoint.distance(self.market.waypoint.coords))
                spread = match.purchase_price - self.sell_price
                arbitrage.append((match.market.waypoint.symbol, distance, spread, round(spread / distance, 2)))
            return sorted(arbitrage, key=lambda x: x[3], reverse=True)
        else:
            return None


class Shipyard(models.Model):
    waypoint = models.OneToOneField(Waypoint, on_delete=models.PROTECT)
    ship_types = ArrayField(base_field=models.CharField(max_length=32), blank=True, null=True)
    modifications_fee = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.waypoint.symbol

    def update(self, data):
        """Update from passed-in data."""
        self.ship_types = [t["type"] for t in data["shipTypes"]]
        self.modifications_fee = data["modificationsFee"]
        self.save()
        if "transactions" in data:
            for t in data["transactions"]:
                transaction, created = ShipyardTransaction.objects.get_or_create(
                    shipyard=self,
                    ship_symbol=t["shipSymbol"],
                    ship_type=t["shipType"],
                    price=t["price"],
                    agent_symbol=t["agentSymbol"],
                    timestamp=t["timestamp"],
                )
        if "ships" in data:
            for s in data["ships"]:
                ship, created = ShipyardShip.objects.get_or_create(
                    shipyard=self,
                    type=s["type"],
                    name=s["name"],
                    description=s["description"],
                )
                ship.supply = s["supply"]
                ship.activity = s["activity"] if "activity" in s else None
                ship.purchase_price = s["purchasePrice"]
                ship.frame = s["frame"]
                ship.reactor = s["reactor"]
                ship.engine = s["engine"]
                ship.crew = s["crew"]
                ship.save()

                # Ship modules
                ship.modules.clear()
                for module_data in s["modules"]:
                    if not ShipModule.objects.filter(symbol=module_data["symbol"]).exists():
                        module = ShipModule(
                            symbol=module_data["symbol"],
                            name=module_data["name"],
                            description=module_data["description"],
                        )
                        if "capacity" in module_data:
                            module.capacity = module_data["capacity"]
                        if "range" in module_data:
                            module.range = module_data["range"]
                        if "requirements" in module_data:
                            module.requirements = module_data["requirements"]
                        module.save()
                    else:
                        module = ShipModule.objects.get(symbol=module_data["symbol"])
                    ship.modules.add(module)

                # Update mounts
                ship.mounts.clear()
                for mount_data in s["mounts"]:
                    if not ShipMount.objects.filter(symbol=mount_data["symbol"]).exists():
                        mount = ShipMount(
                            symbol=mount_data["symbol"],
                            name=mount_data["name"],
                            description=mount_data["description"],
                        )
                        if "strength" in mount_data:
                            mount.strength = mount_data["strength"]
                        if "deposits" in mount_data:
                            mount.deposits = mount_data["deposits"]
                        if "requirements" in mount_data:
                            mount.requirements = mount_data["requirements"]
                        mount.save()
                    else:
                        mount = ShipMount.objects.get(symbol=mount_data["symbol"])
                    ship.mounts.add(mount)

        LOGGER.info(f"{self} shipyard updated")

    @property
    @display(description="ships available")
    def ships_display(self):
        return ", ".join(str(ship) for ship in self.ships.all())


class ShipyardShip(models.Model):
    TYPE_CHOICES = (
        ("SHIP_PROBE", "probe"),
        ("SHIP_MINING_DRONE", "mining drone"),
        ("SHIP_SIPHON_DRONE", "siphon drone"),
        ("SHIP_INTERCEPTOR", "interceptor"),
        ("SHIP_LIGHT_HAULER", "light hauler"),
        ("SHIP_COMMAND_FRIGATE", "command frigate"),
        ("SHIP_EXPLORER", "explorer"),
        ("SHIP_HEAVY_FREIGHTER", "heavy freighter"),
        ("SHIP_LIGHT_SHUTTLE", "light shuttle"),
        ("SHIP_ORE_HOUND", "ore hound"),
        ("SHIP_REFINING_FREIGHTER", "refining freighter"),
        ("SHIP_SURVEYOR", "surveyor"),
    )
    shipyard = models.ForeignKey(Shipyard, related_name="ships", on_delete=models.PROTECT)
    type = models.CharField(max_length=64, choices=TYPE_CHOICES, db_index=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    supply = models.CharField(max_length=32, null=True, blank=True)
    activity = models.CharField(max_length=32, null=True, blank=True)
    purchase_price = models.PositiveIntegerField(default=0)
    frame = models.JSONField(default=dict)
    reactor = models.JSONField(default=dict)
    engine = models.JSONField(default=dict)
    modules = models.ManyToManyField(ShipModule, blank=True)
    mounts = models.ManyToManyField(ShipMount, blank=True)
    crew = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class ShipyardTransaction(models.Model):
    shipyard = models.ForeignKey(Shipyard, related_name="transactions", on_delete=models.CASCADE)
    ship_symbol = models.CharField(max_length=32, null=True, blank=True)  # Deprecated in API
    ship_type = models.CharField(max_length=64)
    price = models.PositiveIntegerField(default=0)
    agent_symbol = models.CharField(max_length=32)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ("timestamp",)

    def __str__(self):
        return f"{self.shipyard} {self.ship_type} for {self.price}"


class Construction(models.Model):
    waypoint = models.OneToOneField(Waypoint, on_delete=models.PROTECT)
    materials = ArrayField(base_field=models.CharField(max_length=32), blank=True, null=True)
    is_complete = models.BooleanField(default=False)

    def update(self, data):
        # TODO
        pass
