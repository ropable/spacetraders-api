from django.contrib.admin import register, ModelAdmin, SimpleListFilter
from .models import (
    Agent,
    Faction,
    System,
    Waypoint,
    WaypointTrait,
    Ship,
    Contract,
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
    readonly_fields = [field.name for field in System._meta.concrete_fields]


@register(Waypoint)
class WaypointAdmin(ReadOnlyModelAdmin):

    class WaypointTraitListFilter(SimpleListFilter):
        title = "trait"
        parameter_name = "trait"

        def lookups(self, request, model_admin):
            return [(wt.symbol, wt.name) for wt in WaypointTrait.objects.all()]

        def queryset(self, request, queryset):
            if self.value():
                trait = WaypointTrait.objects.get(symbol=self.value())
                return queryset.filter(traits__in=[trait])

    list_display = ("symbol", "type", "system", "coords", "faction", "is_under_construction", "modified")
    list_filter = ("type", WaypointTraitListFilter)
    readonly_fields = [field.name for field in Waypoint._meta.concrete_fields]


@register(Ship)
class ShipAdmin(ReadOnlyModelAdmin):
    list_display = ("symbol", "frame_name", "modified")
    readonly_fields = [field.name for field in Ship._meta.concrete_fields]


@register(Contract)
class ContractAdmin(ReadOnlyModelAdmin):
    list_display = ("contract_id", "faction", "type", "terms_deadline", "accepted", "fulfilled", "expiration", "modified")
    readonly_fields = [field.name for field in Contract._meta.concrete_fields] + ["required_goods"]
