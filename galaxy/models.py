from django.contrib.postgres.fields import ArrayField
from django.db import models
from math import dist


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
        return f"{self.symbol} ({self.type})"

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
        return f"{self.symbol} ({self.get_type_display()})"

    def get_type_display(self):
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

    def get_traits(self):
        if self.traits:
            return ', '.join([t.name for t in self.traits.all()])
        else:
            return None


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
        return f"{self.units} units of {self.type}"


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

    def get_exports_display(self):
        return ", ".join([exp.name for exp in self.exports.all()])

    def get_imports_display(self):
        return ", ".join([imp.name for imp in self.imports.all()])

    def get_exchange_display(self):
        return ", ".join([ex.name for ex in self.exchange.all()])

    def update_market(self, data):
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
