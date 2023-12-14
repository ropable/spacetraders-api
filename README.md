# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

Bootstrap database:

```python
from spacetraders import Client
from spacetraders.utils import *
client = Client()
populate_factions(client)
set_agent(client)
populate_ships(client)
populate_contracts(client)
```

# Environment variables

    API_TOKEN
    TZ
    DEBUG
    DATABASE_URL

# TODOs

## Automate mining procurement contract

Inputs:

- Required good(s)
- Source
- Destination
- Ship

Process:

- Navigate to source (pause until arrival)
- Dock
- Refuel
- Extract ore (pause until cooldown)
- Check cargo type and quantity, loop until full
- Navigate to destination
- Dock
- Refuel
- Deliver cargo to contract
- Check delivery terms, fulfill if required, loop to source navigate


- [ ] Find suitable source waypoint (closest with trait)
- [ ] Loop an action with a cooldown period

# Snippets

```
# Visit all of the market waypoints in the system.
ship = Ship.objects.first()
visited_waypoints = []
waypoints_to_visit = list(Waypoint.objects.filter(traits__in=WaypointTrait.objects.filter(symbol='MARKETPLACE')).values_list('symbol', flat=True))

while len(waypoints_to_visit) > 0:
    print(f"len(waypoints_to_visit) waypoints to visit")
    ship.refresh(client)
    # Find the next-nearest waypoint
    waypoints = Waypoint.objects.filter(symbol__in=waypoints_to_visit)
    destinations = []
    for wp in waypoints:
        destinations.append((wp.distance(ship.nav.waypoint.coords), m))
    destinations = sorted(destinations, key=lambda x: x[0])
    destination = destinations[0][1]
    # navigate to destination waypoint
    print(f"Navigating ship to {destination}")
    ship.navigate(client, destination.symbol)
    # pause until arrival
    now = datetime.now(timezone.utc)
    arrival = datetime.fromisoformat(ship.nav.route['arrival'])
    pause = (arrival - now).seconds + 1
    print(f"Pausing {ship.nav.arrival_display()}")
    sleep(pause)
    ship.refresh(client)
    # Refresh waypoint info
    print("Refreshing waypoint info")
    ship.nav.waypoint.refresh(client)
    # Add waypoint symbol to visited_waypoints
    visited_waypoints.append(ship.nav.waypoint.symbol)
    # Remove waypoint from waypoints_to_visit
    waypoints_to_visit.remove(ship.nav.waypoint.symbol)
```
