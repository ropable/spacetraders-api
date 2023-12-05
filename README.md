# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

```python
from spacetraders_api import Client

client = Client()
agent = client.get_agent()
contracts = client.list_contracts()
ships = client.list_ships()
ship = ships[0]
system = client.get_system(ship.nav['systemSymbol'])

# client.list_waypoints works with either a System or symbol.
waypoints = client.list_waypoints(system)

# client.list_waypoints can be filtered by type or by trait.
markets = client.list_waypoints(system.symbol, wp_trait='MARKETPLACE')
for wp in markets:
    if not wp.market:
        data = client.get_market(wp)

# Get the system jump gate
client.list_waypoints(system.symbol, wp_type='JUMP_GATE')

# Find market opportunities
markets = client.list_waypoints(system.symbol, wp_trait='MARKETPLACE')
for wp in markets:
    if not wp.market:
        data = client.get_market(wp)
client.arbitrage_markets(markets)

# Find somewhere to extract resources
origin = ship.get_waypoint()
for wp in waypoints:
    if wp.has_trait('COMMON_METAL_DEPOSITS'):
        d = wp.distance(origin)
        print(wp.symbol.ljust(12), wp.type.ljust(19), '{:.2f}'.format(d).ljust(6), ', '.join([t.symbol for t in wp.traits]))
```
