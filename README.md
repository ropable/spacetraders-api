# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

# Environment variables

    API_TOKEN
    TZ
    DEBUG
    DATABASE_URL

# Bootstrap database

```python
from spacetraders import Client
from galaxy.utils import *
client = Client()
populate_factions(client)  # Populates factions and systems
set_agent(client)  # Creates player Agent instance
populate_ships(client)  # Creates ships and initial system waypoints
populate_contracts(client)
populate_markets(client)
populate_shipyards(client)
```

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

## Find suitable waypoints for mining

```python
waypoints = [wp for wp in Waypoint.objects.all() if (wp.has_trait('COMMON_METAL_DEPOSITS') is True and wp.has_trait('SHALLOW_CRATERS'))]
```

## Visit all of the market waypoints in the system.

```python
from datetime import datetime, timezone
from time import sleep

ship = Ship.objects.first()
visited_waypoints = []
waypoints_to_visit = list(Waypoint.objects.filter(traits__in=WaypointTrait.objects.filter(symbol='MARKETPLACE')).values_list('symbol', flat=True))

while len(waypoints_to_visit) > 0:
    print(f"{len(waypoints_to_visit)} waypoints to visit")
    ship.refresh(client)
    # Find the next-nearest waypoint
    waypoints = Waypoint.objects.filter(symbol__in=waypoints_to_visit)
    destinations = []
    for wp in waypoints:
        destinations.append((wp.distance(ship.nav.waypoint.coords), wp))
    destinations = sorted(destinations, key=lambda x: x[0])
    destination = destinations[0][1]
    # Navigate to destination waypoint
    if ship.nav.waypoint != destination:
        print(f"Navigating ship to {destination}")
        # Try travelling to the waypoint in cruise mode first.
        ship.flight_mode(client, "CRUISE")
        if ship.nav.get_fuel_cost(destination.coords) >= ship.fuel["current"]:
            print("Changing to DRIFT mode")
            ship.flight_mode(client, "DRIFT")
        ship.navigate(client, destination.symbol)
        ship.sleep_until_arrival(client)
        ship.refresh(client)
    # Refresh waypoint info
    print(f"Refreshing waypoint {ship.nav.waypoint} info")
    ship.nav.waypoint.refresh(client)
    # Add waypoint symbol to visited_waypoints
    visited_waypoints.append(ship.nav.waypoint.symbol)
    # Remove waypoint from waypoints_to_visit
    waypoints_to_visit.remove(ship.nav.waypoint.symbol)
    # Refuel ship
    ship.refuel(client)
```

## Find market trade opportunities

```python
market_tradegoods = MarketTradeGood.objects.all()
for exp in market_tradegoods.filter(type="EXPORT"):
    for imp in market_tradegoods.filter(type="IMPORT"):
        if imp.trade_good == exp.trade_good:
            profit = imp.sell_price - exp.purchase_price
            wp_ex = exp.market.waypoint
            wp_im = imp.market.waypoint
            d = wp_ex.distance(wp_im.coords)
            if profit >= 1000 and d <= 250:
                print(wp_ex.symbol.ljust(12), wp_ex.coords, exp.trade_good.symbol.ljust(21), '->', wp_im.symbol.ljust(12), wp_im.coords, f'{profit}/unit', '{:.1f}'.format(d))
```

## Find the longest given trading routes

```python
from spacetraders.utils import get_graph, depth_first_search

market_tradegoods = MarketTradeGood.objects.all()
paths = set()
# First, get a set of all paths (export waypoint, import waypoint).
for exp in market_tradegoods.filter(type="EXPORT"):
    for imp in market_tradegoods.filter(type="IMPORT"):
        if imp.trade_good == exp.trade_good:
            paths.add((exp.market.waypoint.symbol, wp_im.symbol))
graph = get_graph(paths)
starting_waypoint = "X1-BV72-D43"
all_paths = depth_first_search(graph, starting_waypoint)
max_len = max(len(p) for p in all_paths)
max_paths = [p for p in all_paths if len(p) == max_len]

# Choose any of the longest paths.
path = max_paths[0]
path_profit = 0
path_distance = 0
for k, symbol in enumerate(path[:-1]):
    best_profit = 0
    best_distance = 0
    for exp in market_tradegoods.filter(type="EXPORT"):
        for imp in market_tradegoods.filter(type="IMPORT"):
            if imp.trade_good == exp.trade_good:
                wp_ex = exp.market.waypoint
                wp_im = imp.market.waypoint
                if wp_ex.symbol == symbol and wp_im.symbol == path[k+1]:
                    profit = imp.sell_price - exp.purchase_price
                    distance = int(wp_ex.distance(wp_im.coords))
                    if profit > best_profit:
                        best_profit = profit
                        best_distance = distance
                        best_trade = f"{wp_ex.symbol.ljust(12)} {str(wp_ex.coords).ljust(12)} {exp.trade_good.symbol.ljust(21)} -> {wp_im.symbol.ljust(12)} {str(wp_im.coords).ljust(12)} {profit}/unit {distance}"
    path_profit += best_profit
    path_distance += best_distance
    print(best_trade)
print(path_profit, path_distance)
```
