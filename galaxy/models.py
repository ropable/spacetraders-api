from datetime import datetime, timezone
from django.conf import settings
from django.contrib.admin import display
from django.contrib.postgres.fields import ArrayField
from django.db import models
from humanize import naturaldelta
from math import dist
from zoneinfo import ZoneInfo

TZ = ZoneInfo(settings.TIME_ZONE)


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
    traits = models.ManyToManyField(FactionTrait)
    is_recruiting = models.BooleanField(default=False)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Agent(models.Model):
    modified = models.DateTimeField(auto_now=True)
    account_id = models.CharField(max_length=64, unique=True)
    symbol = models.CharField(max_length=32)
    email = models.EmailField(max_length=256, null=True, blank=True)
    starting_faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    headquarters = models.ForeignKey("Waypoint", on_delete=models.PROTECT, null=True, blank=True)
    credits = models.IntegerField(default=0)
    ship_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.symbol} ({self.starting_faction})"

    def update(self, data):
        """Update object from passed-in data."""
        self.credits = data["credits"]
        self.ship_count = data["shipCount"]
        self.save()


class System(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    sector = models.CharField(max_length=32)
    type = models.CharField(max_length=32, db_index=True)
    x = models.IntegerField(editable=False)
    y = models.IntegerField(editable=False)
    factions = models.ManyToManyField(Faction)

    class Meta:
        ordering = ("sector", "symbol")
        unique_together = ("symbol", "sector")

    def __str__(self):
        return f"{self.symbol} ({self.get_type_display()})"

    @property
    def coords(self):
        return (self.x, self.y)

    def get_type_display(self):
        return self.type.replace("_", " ").capitalize()


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
    modified = models.DateTimeField(auto_now=True)
    symbol = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=32, db_index=True)
    system = models.ForeignKey(
        System, related_name="waypoints", on_delete=models.PROTECT, null=True, blank=True)
    x = models.IntegerField(editable=False)
    y = models.IntegerField(editable=False)
    orbits = models.ForeignKey(
        "self", related_name="orbitals", on_delete=models.PROTECT, null=True, blank=True)
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    traits = models.ManyToManyField(WaypointTrait)
    modifiers = models.ManyToManyField(WaypointModifier)
    is_under_construction = models.BooleanField(default=False)

    class Meta:
        ordering = ("symbol",)
        unique_together = ("symbol", "system")

    def __str__(self):
        return f"{self.symbol} ({self.type_display})"

    @property
    @display(description="type")
    def type_display(self):
        return self.type.replace("_", " ").capitalize()

    @property
    def coords(self):
        return (self.x, self.y)

    def has_trait(self, trait):
        if WaypointTrait.objects.filter(symbol=trait).exists() and WaypointTrait.objects.get(symbol=trait) in self.traits.all():
            return True
        else:
            return False

    @property
    def is_market(self):
        return self.has_trait("MARKETPLACE")

    @property
    def is_shipyard(self):
        return self.has_trait("SHIPYARD")

    def distance(self, coords):
        if not isinstance(coords, tuple):
            return False
        return dist((self.x, self.y), (coords[0], coords[1]))

    def traits_display(self):
        if self.traits:
            return ", ".join([t.name for t in self.traits.all()])
        else:
            return ""


class Chart(models.Model):
    waypoint = models.ForeignKey(Waypoint, on_delete=models.CASCADE, null=True, blank=True)
    submitted_by = models.CharField(max_length=32)
    submitted_on = models.DateTimeField()


class ShipNav(models.Model):
    modified = models.DateTimeField(auto_now=True)
    system = models.ForeignKey(System, on_delete=models.PROTECT, null=True, blank=True)
    waypoint = models.ForeignKey(Waypoint, on_delete=models.PROTECT, null=True, blank=True)
    route = models.JSONField(default=dict)
    status = models.CharField(max_length=32)
    flight_mode = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.status} ({self.route['arrival']}), {self.flight_mode}"

    def update(self, data):
        """Update from passed-in nav data."""
        self.system = System.objects.get(symbol=data["systemSymbol"])
        self.waypoint = Waypoint.objects.get(symbol=data["waypointSymbol"])
        self.route = data["route"]
        self.status = data["status"]
        self.flight_mode = data["flightMode"]
        self.save()

    def arrival_display(self):
        """Returns a human-readable string for the arrival time of a ship in transit."""
        if self.status != "IN_TRANSIT":
            return ""
        now = datetime.now(timezone.utc)
        arrival = datetime.fromisoformat(self.route["arrival"])
        return f"{naturaldelta(arrival - now)} ({arrival.astimezone(TZ).strftime('%d/%m/%Y %H:%M')})"


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
    deposits = ArrayField(
        base_field=models.CharField(max_length=32), blank=True, null=True)
    requirements = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Ship(models.Model):
    modified = models.DateTimeField(auto_now=True)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT)
    symbol = models.CharField(max_length=32, unique=True)
    registration = models.JSONField(default=dict)
    nav = models.OneToOneField(ShipNav, on_delete=models.CASCADE)
    crew = models.JSONField(default=dict)
    frame = models.JSONField(default=dict)
    reactor = models.JSONField(default=dict)
    engine = models.JSONField(default=dict)
    cooldown = models.JSONField(default=dict)
    modules = models.ManyToManyField(ShipModule)
    mounts = models.ManyToManyField(ShipMount)
    cargo_capacity = models.PositiveIntegerField(default=0)
    cargo_units = models.PositiveIntegerField(default=0)
    fuel = models.JSONField(default=dict)

    class Meta:
        ordering = ("symbol",)
        unique_together = ("agent", "symbol")

    def __str__(self):
        return f"{self.symbol} ({self.frame['name']})"

    @property
    def frame_name(self):
        return self.frame["name"]

    @property
    def is_docked(self):
        return self.nav.status == "DOCKED"

    def orbit(self, client):
        if not self.is_docked:
            return

        data = client.orbit_ship(self.symbol)
        self.nav.update(data["nav"])

    @property
    def is_in_orbit(self):
        return self.nav.status == "IN_ORBIT"

    def dock(self, client):
        if not self.is_in_orbit:
            return

        data = client.dock_ship(self.symbol)
        self.nav.update(data["nav"])

    def flight_mode(self, client, mode: str):
        """Set the flight mode for this ship."""
        if mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = client.ship_flight_mode(self.symbol, mode)
        # Update ship.nav
        self.nav.update(data)

        return f"{self} flight mode set to {mode}"

    def navigate(self, client, waypoint_symbol):
        if not self.is_in_orbit:
            self.orbit(client)

        data = client.navigate_ship(self.symbol, waypoint_symbol)
        if "error" in data:
            print(data["error"]["message"])
            return False

        # data contains: fuel, nav
        self.fuel = data["fuel"]
        self.save()
        # Update ship.nav
        self.nav.update(data["nav"])

        return f"{self} en route to {self.nav.route['destination']['symbol']}, arrival in {self.nav.arrival_display()}"

    def refuel(self, client, units: int=None, from_cargo: bool=False):
        if not self.is_docked:
            self.dock(client)

        data = client.refuel_ship(self.symbol, units, from_cargo)
        if "error" in data:
            print(data["error"]["message"])
            return False

        # data contains: agent, fuel, transaction
        self.fuel = data["fuel"]
        self.save()
        # Update agent.
        self.agent.update(data["agent"])
        # Create a transaction
        market = Market.objects.get(waypoint__symbol=data["transaction"]["waypointSymbol"])
        trade_good = TradeGood.objects.get(symbol=data["transaction"]["tradeSymbol"])
        Transaction.objects.create(
            market=market,
            ship_symbol=data["transaction"]["shipSymbol"],
            trade_good=trade_good,
            type=data["transaction"]["type"],
            units=data["transaction"]["units"],
            price_per_unit=data["transaction"]["pricePerUnit"],
            total_price=data["transaction"]["totalPrice"],
            timestamp=data["transaction"]["timestamp"],
        )

        return f"{self} refueled {data['transaction']['units']} units"

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

    def purchase_cargo(self, client, commodity, units):
        if not self.is_docked:
            self.dock(client)
        data = client.purchase_cargo(self.symbol, commodity, units)
        if "error" in data:
            print(data["error"]["message"])
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

        return f"{self} purchased {transaction.units} units of {trade_good} for {transaction.total_price}"

    def refresh(self, client):
        data = client.get_ship(self.symbol)
        self.update(data)
        self.update_cargo(data["cargo"])

        return f"{self} data refreshed from server"


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

    def sell(self, client, units=None):
        """Sell this cargo at the ship's current location."""
        # Prevent trying to sell at an invalid location.
        if not self.ship.nav.waypoint.is_market or not self.ship.is_docked or self.units == 0:
            return

        if not units:
            units = self.units

        data = client.sell_cargo(self.ship.symbol, self.type.symbol, units)
        if "error" in data:
            print(data["error"]["message"])
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

        return f"Sold {transaction.units} units of {trade_good} for {transaction.total_price}"


class Contract(models.Model):
    modified = models.DateTimeField(auto_now=True)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT)
    contract_id = models.CharField(max_length=64, unique=True)
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT, null=True, blank=True)
    type = models.CharField(max_length=32)
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


class ContractDeliverGood(models.Model):
    contract = models.ForeignKey(Contract, related_name="deliver_goods", on_delete=models.CASCADE)
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

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.name


class Market(models.Model):
    waypoint = models.OneToOneField(Waypoint, on_delete=models.PROTECT)
    exports = models.ManyToManyField(TradeGood, related_name="exports")
    imports = models.ManyToManyField(TradeGood, related_name="imports")
    exchange = models.ManyToManyField(TradeGood, related_name="exchange")

    def __str__(self):
        return str(self.waypoint)

    @property
    @display(description="exports")
    def exports_display(self):
        return ", ".join([exp.name for exp in self.exports.all()])

    @property
    @display(description="imports")
    def imports_display(self):
        return ", ".join([imp.name for imp in self.imports.all()])

    @property
    @display(description="exchange")
    def exchange_display(self):
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


class Transaction(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    ship_symbol = models.CharField(max_length=32)
    trade_good = models.ForeignKey(TradeGood, on_delete=models.PROTECT)
    type = models.CharField(max_length=32)
    units = models.PositiveIntegerField(default=0)
    price_per_unit = models.PositiveIntegerField(default=0)
    total_price = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ("timestamp",)

    def __str__(self):
        return f"{self.ship_symbol} {self.type.lower()} {self.units} {self.trade_good} for {self.total_price}"


class MarketTradeGood(models.Model):
    modified = models.DateTimeField(auto_now=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    trade_good = models.ForeignKey(TradeGood, on_delete=models.PROTECT)
    type = models.CharField(max_length=32)
    trade_volume = models.PositiveIntegerField(default=0)
    supply = models.CharField(max_length=32)
    activity = models.CharField(max_length=32, null=True, blank=True)
    purchase_price = models.PositiveIntegerField(default=0)
    sell_price = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("market", "trade_good", "type")

    def __str__(self):
        return f"{self.market.waypoint.symbol} - {self.trade_good} ({self.type.lower()})"

    @property
    @display(description="waypoint")
    def waypoint_display(self):
        return str(self.market.waypoint)
