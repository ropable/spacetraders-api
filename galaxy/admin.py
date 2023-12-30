from django.contrib.admin import register, ModelAdmin, SimpleListFilter
from .models import (
    Agent,
    Faction,
    System,
    Waypoint,
    WaypointTrait,
    Ship,
    Contract,
    Market,
    TradeGood,
    MarketTradeGood,
    Shipyard,
    ShipyardShip,
    Transaction,
)


class ReadOnlyModelAdmin(ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@register(Faction)
class FactionAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "name", "headquarters", "is_recruiting")
    fields = [field.name for field in Faction._meta.concrete_fields]


@register(Agent)
class AgentAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "account_id", "email", "starting_faction", "credits", "modified")
    fields = [field.name for field in Agent._meta.concrete_fields]


@register(System)
class SystemAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "sector", "type", "coords")
    list_filter = ("type",)
    fields = [field.name for field in System._meta.concrete_fields]


@register(Waypoint)
class WaypointAdmin(ReadOnlyModelAdmin):

    class WaypointTraitFilter(SimpleListFilter):
        title = "trait"
        parameter_name = "trait"

        def lookups(self, request, model_admin):
            return [(wt.symbol, wt.name) for wt in WaypointTrait.objects.all()]

        def queryset(self, request, queryset):
            if self.value():
                trait = WaypointTrait.objects.get(symbol=self.value())
                return queryset.filter(traits__in=[trait])

    list_display = ("symbol", "type", "system", "coords", "orbits", "faction", "modified")
    list_filter = ("type", "system", "faction", WaypointTraitFilter)
    search_fields = ("symbol",)
    fields = [field.name for field in Waypoint._meta.concrete_fields] + ["orbitals_display"]


@register(WaypointTrait)
class WaypointTraitAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "name", "description")
    fields = [field.name for field in WaypointTrait._meta.concrete_fields]


@register(Ship)
class ShipAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "frame_name", "role", "nav", "behaviour", "modified")
    fields = [field.name for field in Ship._meta.concrete_fields] + ["mounts_display", "modules_display"]


@register(Contract)
class ContractAdmin(ReadOnlyModelAdmin):
    list_display = ("contract_id", "faction", "type", "terms_deadline", "accepted", "fulfilled", "expiration", "modified")
    fields = [field.name for field in Contract._meta.concrete_fields] + ["required_goods"]


@register(TradeGood)
class TradeGoodAdmin(ReadOnlyModelAdmin):
    list_display = ("name", "symbol", "description")
    fields = [field.name for field in TradeGood._meta.concrete_fields]


@register(Market)
class MarketAdmin(ReadOnlyModelAdmin):

    class ImportFilter(SimpleListFilter):
        title = "import"
        parameter_name = "import"

        def lookups(self, request, model_admin):
            return [(good.symbol, good.name) for good in TradeGood.objects.all()]

        def queryset(self, request, queryset):
            if self.value():
                good = TradeGood.objects.get(symbol=self.value())
                return queryset.filter(imports__in=[good])

    class ExportFilter(SimpleListFilter):
        title = "export"
        parameter_name = "export"

        def lookups(self, request, model_admin):
            return [(good.symbol, good.name) for good in TradeGood.objects.all()]

        def queryset(self, request, queryset):
            if self.value():
                good = TradeGood.objects.get(symbol=self.value())
                return queryset.filter(exports__in=[good])

    list_display = ("waypoint", "exports_display", "imports_display", "exchange_display")
    list_filter = (ExportFilter, ImportFilter)
    fields = [field.name for field in Market._meta.concrete_fields]
    search_fields = ("waypoint__symbol", "waypoint__system__symbol")


@register(MarketTradeGood)
class MarketTradeGoodAdmin(ReadOnlyModelAdmin):
    list_display = ("market", "trade_good", "symbol", "type", "supply", "activity", "purchase_price", "sell_price", "trade_volume")
    list_filter = ("type", "supply", "activity", "market")
    fields = [field.name for field in MarketTradeGood._meta.concrete_fields]
    search_fields = ("market__waypoint__symbol", "trade_good__name")


@register(Shipyard)
class ShipyardAdmin(ReadOnlyModelAdmin):
    list_display = ("waypoint", "ships_display", "modifications_fee")
    fields = [field.name for field in Shipyard._meta.concrete_fields]


@register(ShipyardShip)
class ShipyardShipAdmin(ReadOnlyModelAdmin):
    list_display = ("shipyard", "type", "name", "purchase_price")
    fields = [field.name for field in ShipyardShip._meta.concrete_fields]


@register(Transaction)
class TransactionAdmin(ReadOnlyModelAdmin):

    class FuelFilter(SimpleListFilter):
        title = "fuel"
        parameter_name = "fuel"

        def lookups(self, request, model_admin):
            return [(True, "True"), (False, "False")]

        def queryset(self, request, queryset):
            if self.value():
                fuel = TradeGood.objects.get(symbol="FUEL")
                if self.value() == "True":
                    return queryset.filter(trade_good=fuel)
                else:
                    return queryset.exclude(trade_good=fuel)

    date_hierarchy = "timestamp"
    list_display = ("market", "ship_symbol", "trade_good", "type", "units", "total_price", "timestamp")
    list_filter = (FuelFilter, "type", "ship_symbol")
    fields = [field.name for field in Transaction._meta.concrete_fields]
