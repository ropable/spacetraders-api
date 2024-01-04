from django import template

register = template.Library()


@register.simple_tag(name="distance")
def waypoint_distance(origin_waypoint, destination_waypoint):
    return origin_waypoint.distance(destination_waypoint.coords)
