# SpaceTraders API

Reference: https://spacetraders.stoplight.io/docs/spacetraders/11f2735b75b02-space-traders-api

Bootstrap database:

```python
from spacetraders import Client
from spacetraders.utils import populate_factions, populate_ships, set_agent
client = Client()
populate_factions(client)
populate_ships(client)
set_agent(client)
```
