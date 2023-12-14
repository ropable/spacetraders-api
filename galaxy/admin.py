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
    readonly_fields = [field.name for field in Faction._meta.concrete_fields]


@register(Agent)
class AgentAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "account_id", "email", "starting_faction", "credits", "modified")
    readonly_fields = [field.name for field in Agent._meta.concrete_fields]


@register(System)
class SystemAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "sector", "type", "coords")
    list_filter = ("type",)
    readonly_fields = [field.name for field in System._meta.concrete_fields]


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

    list_display = ("symbol", "type_display", "system", "coords", "orbits", "faction", "modified")
    list_filter = ("type", "system", "faction", WaypointTraitFilter)
    search_fields = ("symbol",)
    readonly_fields = [field.name for field in Waypoint._meta.concrete_fields] + ["orbitals_display"]


@register(WaypointTrait)
class WaypointTraitAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "name", "description")
    readonly_fields = [field.name for field in WaypointTrait._meta.concrete_fields]


@register(Ship)
class ShipAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "frame_name", "modified")
    readonly_fields = [field.name for field in Ship._meta.concrete_fields]


@register(Contract)
class ContractAdmin(ReadOnlyModelAdmin):
    list_display = ("contract_id", "faction", "type", "terms_deadline", "accepted", "fulfilled", "expiration", "modified")
    readonly_fields = [field.name for field in Contract._meta.concrete_fields] + ["required_goods"]


@register(TradeGood)
class TradeGoodAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "name", "description")
    readonly_fields = [field.name for field in TradeGood._meta.concrete_fields]


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
    readonly_fields = [field.name for field in Market._meta.concrete_fields]
    search_fields = ("waypoint__symbol",)


@register(MarketTradeGood)
class MarketTradeGoodAdmin(ReadOnlyModelAdmin):

    list_display = ("waypoint_display", "trade_good", "type", "supply", "activity", "purchase_price", "sell_price")
    list_filter = ("type", "supply", "activity")
    readonly_fields = [field.name for field in MarketTradeGood._meta.concrete_fields]
    search_fields = ("market__waypoint__symbol",)
