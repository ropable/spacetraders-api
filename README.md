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

# TODO list

Automate mining procurement contract

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

Problems:

[ ] Find suitable source waypoint (closest with trait)
[ ] Loop an action with a cooldown period
