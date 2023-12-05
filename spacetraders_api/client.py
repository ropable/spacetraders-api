import os
from pathlib import Path
from ratelimit import limits, sleep_and_retry
from requests import Session
from typing import List

from .models import (
    Ship,
    System,
    Waypoint,
    WaypointTrait,
)


d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()


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

    def register_agent(self, symbol: str, faction: str="COSMIC", email: str=None):
        """Register a new agent and ties it to an account.
        """
        # For this method only, pop the Authorization header.
        self.headers.pop("Authorization")
        data = {
            "symbol": symbol,
            "faction": faction,
        }
        if email:
            data["email"] = email
        resp = self.post(f"{self.api_url}/register", json=data)
        resp.raise_for_status()
        data = resp.json()["data"]
        # Re-set the auth header.
        self.headers["Authorization"] = f"Bearer {data['token']}"
        return resp.json()["data"]

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

    def list_factions(self) -> list:
        """Ref: https://spacetraders.stoplight.io/docs/spacetraders/93c5d5e6ad5b0-list-factions
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        factions = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/factions", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                factions += data
                params["page"] += 1

        return factions

    def get_faction(self, symbol: str) -> dict:
        """Ref: https://spacetraders.stoplight.io/docs/spacetraders/a50decd0f9483-get-faction
        """
        resp = self.get(f"{self.api_url}/factions/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

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

        self.ships = [Ship(client=self, **ship) for ship in ships]
        return self.ships

    def get_ship(self, symbol: str) -> Ship:
        """Get the details of a single ship under your ownership.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/800936299c838-get-ship
        """
        resp = self.get(f"{self.api_url}/my/ships/{symbol}")
        resp.raise_for_status()
        data = resp.json()["data"]
        return Ship(client=self, **data)

    def purchase_ship(self, ship_type, waypoint) -> Ship:
        """Purchase a ship from a shipyard.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/403855e2e99ad-purchase-ship
        """
        data = {
            "shipType": ship_type,
        }
        # If the passed-in waypoint is a string, get the Waypoint object.
        if isinstance(waypoint, str):
            data["waypointSymbol"] = waypoint
        else:
            data["waypointSymbol"] = waypoint.symbol

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            return Ship(client=self, **data["ship"])
        except:
            return resp.json()

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
                waypoints.append(Waypoint(client=self, **wp))

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
            waypoints.append(Waypoint(client=self, **wp))

        system["waypoints"] = waypoints
        system = System(**system)
        return system

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_waypoints(self, system, wp_type: str = None, wp_trait: str = None) -> List[Waypoint]:
        """List all waypoints for the given system.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/32186cf59e324-list-waypoints-in-system
        """
        # `system` can either be a System or a string symbol for a system.
        if isinstance(system, str):
            system_symbol = system
        else:
            system_symbol = system.symbol
        # First, determine if client.systems contains a system with this symbol.
        if [s for s in self.systems if s.symbol == system_symbol]:
            system = [s for s in self.systems if s.symbol == system_symbol][0]
            if system.waypoints:  # Return cached data.
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
            wp = Waypoint(client=self, **waypoint)

            if wp.type == "JUMP_GATE":
                wp.get_jump_gate()
            if wp.is_under_construction:
                wp.get_construction_site()
            if wp.has_trait("MARKETPLACE"):
                wp.get_market()

            waypoints.append(wp)

        # Sort waypoints by symbol.
        waypoints = sorted(waypoints, key=lambda x: x.symbol)
        system.waypoints = waypoints
        return self.filter_waypoints(waypoints, wp_type, wp_trait)

    def filter_waypoints(self, waypoints: list, type: str = None, trait: str = None):
        """Filter a list of waypoints by type and/or trait symbol.
        """
        if type:
            waypoints = [wp for wp in waypoints if wp.type == type]
        if trait:
            waypoints = [wp for wp in waypoints if wp.has_trait(trait)]
        return waypoints

    def get_waypoint(self, symbol: str) -> Waypoint:
        """Get a waypoint by symbol.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/58e66f2fa8c82-get-waypoint
        """
        # Infer the system symbol from the waypoint symbol.
        system_symbol = "-".join(symbol.split("-")[0:2])

        # Check if client.systems contains a system with this symbol.
        if self.systems and [s for s in self.systems if s.symbol == system_symbol]:
            system = [s for s in self.systems if s.symbol == system_symbol][0]
            # Check if waypoints for the system have been cached.
            if [wp for wp in system.waypoints if wp.symbol == symbol]:
                return [wp for wp in system.waypoints if wp.symbol == symbol][0]

        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}")
        resp.raise_for_status()
        waypoint = resp.json()["data"]
        waypoint["system_symbol"] = system_symbol

        traits = []
        for trait in waypoint["traits"]:
            traits.append(WaypointTrait(**trait))
        waypoint["traits"] = traits

        return Waypoint(client=self, **waypoint)

    def arbitrage_markets(self, markets, distance_limit=None, return_waypoints=False):
        """For a passed-in list of market waypoints, print markets with matching export -> import goods.
        Optionally limit the output to markets <= `distance_limit` apart.
        """
        exporter_list = set()
        importer_list = set()
        for exporter in markets:
            for export in exporter.market['exports']:
                for importer in markets:
                    for imp in importer.market['imports']:
                        if imp['symbol'] == export['symbol']:
                            distance = exporter.distance(importer)
                            if distance_limit and distance <= distance_limit:
                                exporter_list.add(exporter.symbol)
                                importer_list.add(importer.symbol)
                                print(
                                    exporter.symbol.ljust(12),
                                    exporter.type.ljust(19),
                                    export['symbol'].ljust(15),
                                    '->',
                                    importer.symbol.ljust(12),
                                    importer.type.ljust(19),
                                    '{:.2f}'.format(distance),
                                )
                            elif not distance_limit:
                                exporter_list.add(exporter.symbol)
                                importer_list.add(importer.symbol)
                                print(
                                    exporter.symbol.ljust(12),
                                    exporter.type.ljust(19),
                                    export['symbol'].ljust(15),
                                    '->',
                                    importer.symbol.ljust(12),
                                    importer.type.ljust(19),
                                    '{:.2f}'.format(distance),
                                )

        if return_waypoints:
            return exporter_list, importer_list
