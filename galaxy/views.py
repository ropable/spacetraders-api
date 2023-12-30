from django.http import HttpResponse
from django.views.generic import DetailView, TemplateView
import matplotlib.pyplot as plt

from .models import System, Waypoint


class SystemView(DetailView):
    model = System
    template_name = "galaxy/system_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        system = self.get_object()
        waypoints = Waypoint.objects.filter(system=system)
        context["waypoints"] = [
            {
                "symbol": wp.symbol,
                "type": wp.type,
                "x": wp.x,
                "y": wp.y,
            }
            for wp in waypoints
        ]
        context["minx"] = min([wp.x for wp in waypoints])
        context["miny"] = max([wp.y for wp in waypoints])
        context["width"] = max([wp.x for wp in waypoints]) + context["minx"]
        context["height"] = context["miny"] + min([wp.y for wp in waypoints])
        return context


class SystemImageView(DetailView):

    model = System

    def get(self, request, *args, **kwargs):
        system = self.get_object()
        plotted_points = set()
        plt.figure()
        plt.title(system)

        # Plot system star
        for wp in Waypoint.objects.filter(system=system, type="GAS_GIANT"):
            plt.plot(wp.x, wp.y, color="yellow", marker="*")
            plt.annotate(
                text=wp.symbol_suffix,
                xy=(wp.x + 15, wp.y - 10),
            )
            plotted_points.add(wp.coords)

        # Plot jump gates
        for wp in Waypoint.objects.filter(system=system, type="JUMP_GATE"):
            plt.plot(wp.x, wp.y, color="blue", marker="h")
            plt.annotate(
                text=wp.symbol_suffix,
                xy=(wp.x + 15, wp.y - 10),
            )
            plotted_points.add(wp.coords)

        # Plot planets
        for wp in Waypoint.objects.filter(system=system, type="PLANET"):
            plt.plot(wp.x, wp.y, color="green", marker="o")
            plt.annotate(
                text=wp.symbol_suffix,
                xy=(wp.x + 15, wp.y - 10),
            )
            plotted_points.add(wp.coords)

        # Plot everything else
        for wp in Waypoint.objects.filter(system=system).exclude(type__in=["JUMP_GATE", "PLANET"]):
            if wp.coords not in plotted_points:
                plt.plot(wp.x, wp.y, color="red", marker="x")
                #plt.annotate(
                #    text=wp.symbol_suffix,
                #    xy=(wp.x + 5, wp.y),
                #)
                plotted_points.add(wp.coords)

        response = HttpResponse(content_type="image/png")
        plt.savefig(response, format="png")

        return response
