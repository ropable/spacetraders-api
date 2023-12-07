from django.contrib.postgres.fields import ArrayField
from django.db import models
from math import dist


class FactionTrait(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Faction(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    headquarters = models.ForeignKey("System", on_delete=models.PROTECT, null=True, blank=True)
    traits = models.ManyToManyField(FactionTrait)
    is_recruiting = models.BooleanField(editable=False)

    def __str__(self):
        return self.name


class Agent(models.Model):
    modified = models.DateTimeField(auto_now=True)
    account_id = models.CharField(max_length=64, unique=True)
    symbol = models.CharField(max_length=32)
    email = models.EmailField(max_length=256, null=True, blank=True)
    starting_faction = models.ForeignKey(
        Faction, on_delete=models.PROTECT, null=True, blank=True)
    headquarters = models.ForeignKey(
        "Waypoint", on_delete=models.PROTECT, null=True, blank=True)
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

    def __str__(self):
        return f"{self.symbol} ({self.type})"

    @property
    def coords(self):
        return (self.x, self.y)


class WaypointTrait(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class WaypointModifier(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

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

    def __str__(self):
        return f"{self.symbol} ({self.type})"

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
    waypoint = models.ForeignKey(
        Waypoint, on_delete=models.CASCADE, null=True, blank=True)
    submitted_by = models.CharField(max_length=32)
    submitted_on = models.DateTimeField(editable=False)


class ShipNav(models.Model):
    modified = models.DateTimeField(auto_now=True)
    system = models.ForeignKey(System, on_delete=models.PROTECT, null=True, blank=True)
    waypoint = models.ForeignKey(Waypoint, on_delete=models.PROTECT, null=True, blank=True)
    route = models.JSONField(default=dict)  # TODO: dedicated model
    status = models.CharField(max_length=32)
    flight_mode = models.CharField(max_length=32)


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
    symbol = models.CharField(max_length=32, unique=True)
    registration = models.JSONField(default=dict)
    nav = models.OneToOneField(ShipNav, on_delete=models.CASCADE)
    crew = models.JSONField(default=dict)  # TODO: dedicated model
    frame = models.JSONField(default=dict)  # TODO: dedicated model
    reactor = models.JSONField(default=dict)  # TODO: dedicated model
    engine = models.JSONField(default=dict)  # TODO: dedicated model
    cooldown = models.JSONField(default=dict)  # TODO: dedicated model
    modules = models.ManyToManyField(ShipModule)
    mounts = models.ManyToManyField(ShipMount)
    cargo_capacity = models.PositiveIntegerField(default=0)
    cargo_units = models.PositiveIntegerField(default=0)
    fuel = models.JSONField(default=dict)  # TODO: dedicated model

    def __str__(self):
        return f"{self.symbol} ({self.frame['name']})"

    @property
    def frame_name(self):
        return self.frame["name"]


class CargoType(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class ShipCargoItem(models.Model):
    type = models.ForeignKey(CargoType, on_delete=models.PROTECT, null=True, blank=True)
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, null=True, blank=True)
    units = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.units} units of {self.type}"
