# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

# TODOs

 - [ ] Allow ship navigation between waypoints (GUI)
 - [ ] Allow cargo purchase/sale at markets (GUI)
 - [ ] A* pathing search for navigating ships
 - [ ] Galaxy (all systems) view

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

# Register a new agent

Register a new agent and obtain a bearer token (in addition to returning the
token in the response, this method writes the token value out to a file).

```python
from spacetraders import Client

client = Client()
data = client.register_agent("new_agent")
```

# Queue worker & scheduler

```
poetry run python manage.py rqworker --with-scheduler
```

# Frontend

Stylesheets:

- https://codepen.io/dragontheory/pen/wvRRYqQ
- https://gist.github.com/CodeMyUI/1d83fbd4904edd7021c06f8dfd0f14c9
- https://terminalcss.xyz/dark/

# TODOs

## Autonomous trading behaviour

- [X] Find nearest market(s) with exports
- [X] Find export with best / most efficient spread
- [X] Select trade good, destination, quantity
- [X] Purchase desired quantity of trade good
- [X] Navigate to destination
- [X] Wait on arrival
- [X] Sell trade good

- [ ] Define a series of tasks, which might have sub-tasks
- [ ] Find the "active" task and determine what needs to be done next
- [ ] Introduce some randomisation into how ships find an export market

```
ship = Ship.objects.first()

if not ship.nav.waypoint.market.exports.all():  # No exports at this market.
    export_markets = ship.nav.get_export_markets()
    # Navigate to the nearest market having exports.
    destination = Waypoint.objects.get(symbol=export_markets[0][0])
    if ship.nav.get_fuel_cost(destination.coords) >= ship.fuel["current"]:
        ship.flight_mode(client, "DRIFT")
    else:
        ship.flight_mode(client, "CRUISE")
    ship.navigate(client, destination.symbol)
    ship.sleep_until_arrival()
    ship.refuel(client)

spread, trade_good_symbol, waypoint_symbol = ship.nav.waypoint.market.get_best_export()
destination = Waypoint.objects.get(symbol=waypoint_symbol)
ship.purchase_cargo(client, trade_good_symbol)
ship.nav.waypoint.refresh(client)
if ship.nav.get_fuel_cost(destination.coords) >= ship.fuel["current"]:
    ship.flight_mode(client, "DRIFT")
else:
    ship.flight_mode(client, "CRUISE")
ship.navigate(client, waypoint_symbol)
ship.sleep_until_arrival()
ship.sell_cargo(client)
ship.refuel(client)
ship.nav.waypoint.refresh(client)
```

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
        ship.sleep_until_arrival()
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

## Find the nearest export markets to a ship

```python
system = ship.nav.waypoint.system
export_markets = Market.objects.filter(exports__isnull=False, waypoint__system=system).distinct()
export_waypoints = [(e.waypoint, e.waypoint.distance(ship.nav.waypoint.coords), e.exports_display) for e in export_markets]
export_waypoints = sorted(export_waypoints, key=lambda x: x[1])
```

## Find market export/import opportunities

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
