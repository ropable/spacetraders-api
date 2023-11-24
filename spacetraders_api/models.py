import os
from math import sqrt
from pathlib import Path
from pydantic import BaseModel, Field
from ratelimit import limits, sleep_and_retry
from requests import Session
from typing import List, Any


d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()


class Ship(BaseModel):

    symbol: str
    registration: dict
    nav: dict
    crew: dict
    frame: dict
    reactor: dict
    engine: dict
    cooldown: dict
    modules: List[dict]
    mounts: List[dict]
    cargo: dict
    fuel: dict

    @property
    def waypoint_symbol(self) -> str:

        return self.nav["waypointSymbol"]

    def get_waypoint(self, client):
        """Returns the waypoint where this ship is located.
        """
        return client.get_waypoint(self.nav["systemSymbol"], self.nav["waypointSymbol"])

    def flight_mode(self, client, flight_mode: str):
        """Set the flight mode for this ship.
        """
        if flight_mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = {
            "flightMode": flight_mode,
        }
        resp = client.patch(f"{client.api_url}/my/ships/{self.symbol}/nav", json=data)
        resp.raise_for_status()
        return resp.json()["data"]

    def navigate(self, client, waypoint):

        # TODO test: in orbit (not docked)
        # TODO test: within range
        data = {
            "waypointSymbol": waypoint.symbol,
        }
        try:
            resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/navigate", json=data)
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            return resp.json()

    def orbit(self, client):
        """Attempt to move this ship into orbit at the current location.
        """
        resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/orbit")
        resp.raise_for_status()
        return resp.json()["data"]

    def dock(self, client):
        """Dock this ship at the current location.
        """
        resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/dock")
        resp.raise_for_status()
        return resp.json()["data"]

    def sell_cargo(self, client, commodity: str, units: int):
        """Sell cargo in a given ship to a marketplace.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b8ed791381b41-sell-cargo
        """
        data = {
            "symbol": commodity,
            "units": units,
        }

        try:
            resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/sell", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def refuel(self, client, units: int = None, from_cargo: bool = False):

        data = {"fromCargo": from_cargo}
        if units:
            data["units": units]

        try:
            resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/refuel", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship fuel.
            self.fuel = data["fuel"]
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def survey(self, client):
        pass

    def extract(self, client):
        pass


class WaypointTrait(BaseModel):

    symbol: str
    name: str
    description: str


class Waypoint(BaseModel):

    symbol: str
    type: str
    system_symbol: str
    x: int
    y: int
    orbitals: List[dict]
    orbits: str = None
    faction: dict = None
    traits: List = None
    modifiers: List[dict] = None
    chart: dict = None
    is_under_construction: Any = None
    market: dict = None
    # TODO: market info age / expiry.

    @property
    def coords(self):
        """Return the x, y coordinates of this waypoint as a tuple.
        """
        return (self.x, self.y)

    def has_trait(self, symbol: str):
        """Returns boolean based on whether this waypoint has the given trait symbol.
        """
        for trait in self.traits:
            if trait.symbol == symbol:
                return True

        return False

    def distance(self, waypoint):
        """Calculate the distance from this waypoint to the passed-in waypoint.
        Ref: https://www.omnicalculator.com/math/coordinate-distance
        """
        x1, y1 = self.x, self.y
        x2, y2 = waypoint.x, waypoint.y
        d = (x2 - x1)**2 + (y2 - y1)**2
        return sqrt(d)

    def get_market(self, client):
        """Retrieves import, export and exchange data for this waypoint if it has the
        MARKETPLACE trait, otherwise returns None.
        """
        if not self.has_trait("MARKETPLACE"):
            return None

        if self.market:
            return self.market  # Return cached data.

        resp = client.get(f"{client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/market")
        resp.raise_for_status()
        self.market = resp.json()["data"]

    @property
    def imports(self):

        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["imports"]])

    @property
    def exports(self):

        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["exports"]])

    @property
    def exchange(self):

        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["exchange"]])


class System(BaseModel):

    symbol: str
    sector_symbol: str = Field(alias="sectorSymbol")
    type: str
    x: int
    y: int
    waypoints: List
    factions: List
    waypoints_cached: bool = False


class Client(Session):
    """An authenticated Spacetraders HTTP client having methods named after each of the
    API endpoints.
    """
    def __init__(self, token=None, api_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if token is None:
            self.token = os.environ.get("API_TOKEN")
        else:
            self.token = token

        if api_url is None:
            # Default to using the v2 API.
            self.api_url = "https://api.spacetraders.io/v2"
        else:
            self.api_url = api_url

        self.headers["Accept"] = "application/json"
        self.headers["Content-Type"] = "application/json"
        self.headers["Authorization"] = f"Bearer {self.token}"

        self.systems = []
        self.ships = []

    def get_status(self) -> dict:
        """Get server status (does not require authentication).
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/7534550e1ba52-get-status
        """
        resp = self.get(f"{self.api_url}/")
        resp.raise_for_status()
        return resp.json()

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_agents(self) -> list:
        """List all agent details.
        https://spacetraders.stoplight.io/docs/spacetraders/d4567f6f3c159-list-agents
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        agents = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/agents", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                agents += data
                params["page"] += 1

        return agents

    def get_agent(self) -> dict:
        """Fetch your own agent's details.
        https://spacetraders.stoplight.io/docs/spacetraders/eb030b06e0192-get-agent
        """
        resp = self.get(f"{self.api_url}/my/agent")
        resp.raise_for_status()
        return resp.json()["data"]

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_contracts(self) -> list:
        """List all of your contracts.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b5d513949b11a-list-contracts
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        contracts = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/my/contracts", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                contracts += data
                params["page"] += 1

        return contracts

    def get_contract(self, contract_id: str) -> dict:
        """Get the details of a single contract by ID.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/2889d8b056533-get-contract
        """
        resp = self.get(f"{self.api_url}/my/contracts/{contract_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def accept_contract(self, contract_id: str) -> dict:
        """Accept a contract by ID.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/7dbc359629250-accept-contract
        """
        resp = self.post(f"{self.api_url}/my/contracts/{contract_id}/accept")
        resp.raise_for_status()
        return resp.json()["data"]["contract"]

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_ships(self) -> List[Ship]:
        """List all of the ships under your ownership.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/64435cafd9005-list-ships
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        ships = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/my/ships", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                ships += data
                params["page"] += 1

        self.ships = [Ship(**ship) for ship in ships]
        return self.ships

    def get_ship(self, ship_symbol: str) -> Ship:
        """Get the details of a single ship under your ownership.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/800936299c838-get-ship
        """
        resp = self.get(f"{self.api_url}/my/ships/{ship_symbol}")
        resp.raise_for_status()
        data = resp.json()["data"]
        return Ship(**data)

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_systems(self) -> List[System]:
        """List all systems
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/94269411483d0-list-systems
        """
        if self.systems:  # Return cached systems.
            return self.systems

        params = {
            "limit": 20,
            "page": 1,
        }
        systems_data = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/systems", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                systems_data += data
                params["page"] += 1

        systems = []
        for system in systems_data:
            waypoints = []
            for wp in system["waypoints"]:
                wp["system_symbol"] = system["symbol"]
                waypoints.append(Waypoint(**wp))

            system["waypoints"] = waypoints
            systems.append(System(**system))

        self.systems = systems  # Cache systems.
        return self.systems

    def get_system(self, symbol: str) -> System:
        """Get the details for a single system.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/67e77e75c65e7-get-system
        """
        # Check if client.systems contains a system with this symbol.
        if self.systems and [s for s in self.systems if s.symbol == symbol]:
            return [s for s in self.systems if s.symbol == symbol][0]

        resp = self.get(f"{self.api_url}/systems/{symbol}")
        resp.raise_for_status()
        system = resp.json()["data"]

        waypoints = []
        for wp in system["waypoints"]:
            wp["system_symbol"] = system["symbol"]
            waypoints.append(Waypoint(**wp))

        system["waypoints"] = waypoints
        system = System(**system)
        return system

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_waypoints(self, system_symbol: str, wp_type: str = None, wp_trait: str = None) -> List[Waypoint]:
        """List all waypoints for the given system.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/32186cf59e324-list-waypoints-in-system
        """
        # First, determine if client.systems contains a system with this symbol.
        if [s for s in self.systems if s.symbol == system_symbol]:
            system = [s for s in self.systems if s.symbol == system_symbol][0]
            if system.waypoints_cached and system.waypoints:  # Return cached data.
                return self.filter_waypoints(system.waypoints, wp_type, wp_trait)
        else:
            system = self.get_system(system_symbol)
            self.systems.append(system)

        params = {
            "limit": 20,
            "page": 1,
        }
        waypoints_data = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                waypoints_data += data
                params["page"] += 1

        waypoints = []
        for waypoint in waypoints_data:
            waypoint["system_symbol"] = system_symbol
            traits = []
            for trait in waypoint["traits"]:
                traits.append(WaypointTrait(**trait))
            waypoint["traits"] = traits
            waypoints.append(Waypoint(**waypoint))

        system.waypoints = waypoints
        system.waypoints_cached = True

        return self.filter_waypoints(waypoints, wp_type, wp_trait)

    def filter_waypoints(self, waypoints: list, type: str = None, trait: str = None):
        """Filter a list of waypoints by type and/or trait symbol.
        """
        if type:
            waypoints = [wp for wp in waypoints if wp.type == type]
        if trait:
            waypoints = [wp for wp in waypoints if wp.has_trait(trait)]
        return waypoints

    def get_waypoint(self, system_symbol: str, waypoint_symbol: str):
        """Get the details for a single waypoint.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/58e66f2fa8c82-get-waypoint
        """
        # Check if client.systems contains a system with this symbol.
        if self.systems and [s for s in self.systems if s.symbol == system_symbol]:
            system = [s for s in self.systems if s.symbol == system_symbol][0]
            # Check if waypoints for the system have been cached.
            if system.waypoints_cached and [wp for wp in system.waypoints if wp.symbol == waypoint_symbol]:
                return [wp for wp in system.waypoints if wp.symbol == waypoint_symbol][0]

        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{waypoint_symbol}")
        resp.raise_for_status()
        waypoint = resp.json()["data"]
        waypoint["system_symbol"] = system_symbol

        traits = []
        for trait in waypoint["traits"]:
            traits.append(WaypointTrait(**trait))
        waypoint["traits"] = traits

        return Waypoint(**waypoint)

    def get_market(self, waypoint) -> dict:
        """Get import, export & exchange data for a marketplace.
        This differs from the Waypoint.get_market method in that it always makes a HTTP request.
        """
        if not waypoint.has_trait("MARKETPLACE"):
            return None

        resp = self.get(f"{self.api_url}/systems/{waypoint.system_symbol}/waypoints/{waypoint.symbol}/market")
        resp.raise_for_status()

        # Cache the market data on the waypoint.
        waypoint.market = resp.json()["data"]
        return waypoint.market
