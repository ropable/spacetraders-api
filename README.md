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
