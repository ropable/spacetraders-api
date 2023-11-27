# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

```
from spacetraders_api import Client

client = Client()
agent = client.get_agent()
contracts = client.list_contracts()
ships = client.list_ships()
ship = ships[0]
system_symbol = ship.nav['systemSymbol']
system = client.get_system(system_symbol)
waypoints = client.list_waypoints(system.symbol)
markets = client.list_waypoints(system.symbol, wp_trait='MARKETPLACE')
for wp in markets:
    if not wp.market:
        data = client.get_market(wp)
```
