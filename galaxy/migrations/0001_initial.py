# Generated by Django 4.2.8 on 2024-01-02 02:01

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Agent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("account_id", models.CharField(max_length=64, unique=True)),
                ("symbol", models.CharField(max_length=32)),
                ("email", models.EmailField(blank=True, max_length=256, null=True)),
                ("credits", models.IntegerField(default=0)),
                ("ship_count", models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="CargoType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="Contract",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("contract_id", models.CharField(max_length=64, unique=True)),
                ("type", models.CharField(max_length=32)),
                ("terms_deadline", models.DateTimeField()),
                ("terms_payment", models.JSONField(default=dict)),
                ("accepted", models.BooleanField(default=False)),
                ("fulfilled", models.BooleanField(default=False)),
                ("expiration", models.DateTimeField()),
                ("deadline_to_accept", models.DateTimeField()),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="galaxy.agent"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Faction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
                ("is_recruiting", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="FactionTrait",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="Market",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ShipModule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
                ("capacity", models.PositiveIntegerField(default=0)),
                ("range", models.PositiveIntegerField(default=0)),
                ("requirements", models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="ShipMount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
                ("strength", models.PositiveIntegerField(default=0)),
                (
                    "deposits",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=32),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                ("requirements", models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="Shipyard",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ship_types",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=32),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                ("modifications_fee", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="System",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("sector", models.CharField(max_length=32)),
                ("type", models.CharField(db_index=True, max_length=32)),
                ("x", models.IntegerField(editable=False)),
                ("y", models.IntegerField(editable=False)),
                ("factions", models.ManyToManyField(blank=True, to="galaxy.faction")),
            ],
            options={
                "ordering": ("sector", "symbol"),
                "unique_together": {("symbol", "sector")},
            },
        ),
        migrations.CreateModel(
            name="TradeGood",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField()),
                ("inputs", models.ManyToManyField(blank=True, to="galaxy.tradegood")),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="WaypointModifier",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="WaypointTrait",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ("symbol",),
            },
        ),
        migrations.CreateModel(
            name="Waypoint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("type", models.CharField(db_index=True, max_length=32)),
                ("x", models.IntegerField(editable=False)),
                ("y", models.IntegerField(editable=False)),
                ("is_under_construction", models.BooleanField(default=False)),
                (
                    "faction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.faction",
                    ),
                ),
                (
                    "modifiers",
                    models.ManyToManyField(blank=True, to="galaxy.waypointmodifier"),
                ),
                (
                    "orbits",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orbitals",
                        to="galaxy.waypoint",
                    ),
                ),
                (
                    "system",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="waypoints",
                        to="galaxy.system",
                    ),
                ),
                (
                    "traits",
                    models.ManyToManyField(blank=True, to="galaxy.waypointtrait"),
                ),
            ],
            options={
                "ordering": ("symbol",),
                "unique_together": {("symbol", "system")},
            },
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ship_symbol", models.CharField(max_length=32)),
                ("type", models.CharField(max_length=32)),
                ("units", models.PositiveIntegerField(default=0)),
                ("price_per_unit", models.PositiveIntegerField(default=0)),
                ("total_price", models.PositiveIntegerField(default=0)),
                ("timestamp", models.DateTimeField()),
                (
                    "market",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="galaxy.market"
                    ),
                ),
                (
                    "trade_good",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.tradegood",
                    ),
                ),
            ],
            options={
                "ordering": ("-timestamp",),
            },
        ),
        migrations.CreateModel(
            name="ShipyardTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ship_symbol", models.CharField(blank=True, max_length=32, null=True)),
                ("ship_type", models.CharField(max_length=64)),
                ("price", models.PositiveIntegerField(default=0)),
                (
                    "agent_symbol",
                    models.CharField(blank=True, max_length=32, null=True),
                ),
                ("timestamp", models.DateTimeField()),
                (
                    "shipyard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="galaxy.shipyard",
                    ),
                ),
            ],
            options={
                "ordering": ("timestamp",),
            },
        ),
        migrations.CreateModel(
            name="ShipyardShip",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("type", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, null=True)),
                ("supply", models.CharField(blank=True, max_length=32, null=True)),
                ("activity", models.CharField(blank=True, max_length=32, null=True)),
                ("purchase_price", models.PositiveIntegerField(default=0)),
                ("frame", models.JSONField(default=dict)),
                ("reactor", models.JSONField(default=dict)),
                ("engine", models.JSONField(default=dict)),
                ("crew", models.JSONField(default=dict)),
                ("modules", models.ManyToManyField(blank=True, to="galaxy.shipmodule")),
                ("mounts", models.ManyToManyField(blank=True, to="galaxy.shipmount")),
                (
                    "shipyard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ships",
                        to="galaxy.shipyard",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="shipyard",
            name="waypoint",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT, to="galaxy.waypoint"
            ),
        ),
        migrations.CreateModel(
            name="ShipNav",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("route", models.JSONField(default=dict)),
                ("status", models.CharField(max_length=32)),
                ("flight_mode", models.CharField(max_length=32)),
                (
                    "system",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.system",
                    ),
                ),
                (
                    "waypoint",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.waypoint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Ship",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("symbol", models.CharField(max_length=32, unique=True)),
                ("registration", models.JSONField(default=dict)),
                ("crew", models.JSONField(default=dict)),
                ("frame", models.JSONField(default=dict)),
                ("reactor", models.JSONField(default=dict)),
                ("engine", models.JSONField(default=dict)),
                ("cooldown", models.JSONField(default=dict)),
                ("cargo_capacity", models.PositiveIntegerField(default=0)),
                ("cargo_units", models.PositiveIntegerField(default=0)),
                ("fuel", models.JSONField(default=dict)),
                (
                    "behaviour",
                    models.CharField(
                        blank=True,
                        choices=[
                            (None, "None"),
                            ("TRADE", "Trading"),
                            ("MINE", "Mining"),
                            ("HAUL", "Hauling"),
                        ],
                        help_text="Desired autonomous behaviour",
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="galaxy.agent"
                    ),
                ),
                ("modules", models.ManyToManyField(blank=True, to="galaxy.shipmodule")),
                ("mounts", models.ManyToManyField(blank=True, to="galaxy.shipmount")),
                (
                    "nav",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="galaxy.shipnav"
                    ),
                ),
            ],
            options={
                "ordering": ("symbol",),
                "unique_together": {("agent", "symbol")},
            },
        ),
        migrations.AddField(
            model_name="market",
            name="exchange",
            field=models.ManyToManyField(
                blank=True, related_name="exchange", to="galaxy.tradegood"
            ),
        ),
        migrations.AddField(
            model_name="market",
            name="exports",
            field=models.ManyToManyField(
                blank=True, related_name="exports", to="galaxy.tradegood"
            ),
        ),
        migrations.AddField(
            model_name="market",
            name="imports",
            field=models.ManyToManyField(
                blank=True, related_name="imports", to="galaxy.tradegood"
            ),
        ),
        migrations.AddField(
            model_name="market",
            name="waypoint",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT, to="galaxy.waypoint"
            ),
        ),
        migrations.AddField(
            model_name="faction",
            name="headquarters",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="galaxy.system",
            ),
        ),
        migrations.AddField(
            model_name="faction",
            name="traits",
            field=models.ManyToManyField(blank=True, to="galaxy.factiontrait"),
        ),
        migrations.CreateModel(
            name="ContractDeliverGood",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("symbol", models.CharField(max_length=128)),
                ("units_required", models.PositiveIntegerField(default=0)),
                ("units_fulfilled", models.PositiveIntegerField(default=0)),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliver_goods",
                        to="galaxy.contract",
                    ),
                ),
                (
                    "destination",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.waypoint",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="contract",
            name="faction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="galaxy.faction",
            ),
        ),
        migrations.CreateModel(
            name="Construction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "materials",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=32),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                ("is_complete", models.BooleanField(default=False)),
                (
                    "waypoint",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.waypoint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Chart",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("submitted_by", models.CharField(max_length=32)),
                ("submitted_on", models.DateTimeField()),
                (
                    "waypoint",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="galaxy.waypoint",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="agent",
            name="headquarters",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="galaxy.waypoint",
            ),
        ),
        migrations.AddField(
            model_name="agent",
            name="starting_faction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="galaxy.faction",
            ),
        ),
        migrations.CreateModel(
            name="ShipCargoItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("units", models.PositiveIntegerField(default=0)),
                (
                    "ship",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cargo",
                        to="galaxy.ship",
                    ),
                ),
                (
                    "type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.cargotype",
                    ),
                ),
            ],
            options={
                "unique_together": {("type", "ship")},
            },
        ),
        migrations.CreateModel(
            name="MarketTradeGood",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("modified", models.DateTimeField(auto_now=True)),
                ("type", models.CharField(max_length=32)),
                ("trade_volume", models.PositiveIntegerField(default=0)),
                ("supply", models.CharField(max_length=32)),
                ("activity", models.CharField(blank=True, max_length=32, null=True)),
                ("purchase_price", models.PositiveIntegerField(default=0)),
                ("sell_price", models.PositiveIntegerField(default=0)),
                (
                    "market",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="galaxy.market"
                    ),
                ),
                (
                    "trade_good",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="galaxy.tradegood",
                    ),
                ),
                (
                    "trade_matches",
                    models.ManyToManyField(blank=True, to="galaxy.markettradegood"),
                ),
            ],
            options={
                "unique_together": {("market", "trade_good", "type")},
            },
        ),
    ]
