import datetime

from django.conf import settings

from route_api.models import Route


def does_route_exist(date:datetime.date, waypoint_start:tuple, waypoint_end:tuple):
    """ Check if a route of given parameters has already been calculated. 
    Return False if not and the route object if it has.
    """
    # TODO account for tolerance of waypoint location in linear distance

    routes = Route.objects.filter(
        calculated__date=date,
        waypoint_start__exact=waypoint_start,
        waypoint_end__exact=waypoint_end,
    )

    if len(routes) < 1:
        return False
    else:
        return routes
    
    