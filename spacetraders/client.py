import os
from pathlib import Path
from ratelimit import limits, sleep_and_retry
from requests import Session


d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()


class Client(Session):
    """A Spacetraders HTTP client having methods named after each of the
    API endpoints. Derives the authentication token from the `API_TOKEN`
    environment variable.
    """
    def __init__(self, token=None, api_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if token is None:
            self.token = os.environ.get("API_TOKEN")
        else:
            self.token = token

        if api_url is None:
            if os.environ.get("API_URL", None):
                self.api_url = os.environ.get("API_URL")
            else:
                # Default to using the v2 API.
                self.api_url = "https://api.spacetraders.io/v2"
        else:
            self.api_url = api_url

        self.headers["Accept"] = "application/json"
        self.headers["Content-Type"] = "application/json"

        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_server_status(self):
        """Get server status.
        """
        resp = self.get(f"{self.api_url}/")
        resp.raise_for_status()
        return resp.json()

    def register_agent(self, symbol: str, email: str = None, faction: str = "COSMIC"):
        """Register a new player agent and return an authentication token.
        """
        if self.token:
            raise Exception("Already configured with token")

        data = {
            "faction": faction,
            "symbol": symbol,
        }
        if email:
            data["emai"] = email

        resp = self.post(f"{self.api_url}/register", json=data)
        resp.raise_for_status()
        data = resp.json()["data"]

        token = open("BEARER_TOKEN", "w")
        token.write(data["token"])
        print("Token written to file")
        return data

    # ----------------------------------------------------------------
    # Agents endpoints
    # ----------------------------------------------------------------
    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_agents(self):
        """List all agent details.
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

    def get_agent(self):
        """Get the player agent's details from the game server.
        """
        resp = self.get(f"{self.api_url}/my/agent")
        resp.raise_for_status()
        return resp.json()["data"]

    # ----------------------------------------------------------------
    # Contracts endpoints
    # ----------------------------------------------------------------
    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_contracts(self):
        """List all player contracts.
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

    def get_contract(self, contract_id):
        """Get a single contract's details.
        """
        resp = self.get(f"{self.api_url}/my/contracts/{contract_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def accept_contract(self, contract_id):
        """Accept a single contract.
        """
        resp = self.post(f"{self.api_url}/my/contracts/{contract_id}/accept")
        resp.raise_for_status()
        return resp.json()["data"]

    # TODO: deliver_cargo_to_contract
    # TODO: fulfill_contract

    # ----------------------------------------------------------------
    # Factions endpoints
    # ----------------------------------------------------------------
    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_factions(self):
        """List all faction details.
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

    def get_faction(self, symbol: str):
        """Fetch a single factions's details.
        """
        resp = self.get(f"{self.api_url}/factions/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    # ----------------------------------------------------------------
    # Fleet endpoints
    # ----------------------------------------------------------------
    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_ships(self):
        """List all of the ships under the player's ownership.
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

        return ships

    def get_ship(self, symbol: str):
        """Get the details of a single ship under the player's ownership.
        """
        resp = self.get(f"{self.api_url}/my/ships/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    def orbit_ship(self, symbol: str):
        """Attempt to move a ship into orbit.
        """
        resp = self.post(f"{self.api_url}/my/ships/{symbol}/orbit")
        resp.raise_for_status()
        return resp.json()["data"]

    def dock_ship(self, symbol: str):
        """Attempt to dock a ship at the current location.
        """
        resp = self.post(f"{self.api_url}/my/ships/{symbol}/dock")
        resp.raise_for_status()
        return resp.json()["data"]

    def ship_flight_mode(self, symbol: str, flight_mode: str):
        """Set the flight mode for this ship.
        """
        if flight_mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = {
            "flightMode": flight_mode,
        }
        resp = self.patch(f"{self.api_url}/my/ships/{symbol}/nav", json=data)
        resp.raise_for_status()
        return resp.json()["data"]

    def navigate_ship(self, symbol: str, waypoint: str):
        """Attempt to navigate ship to the nominated waypoint.
        """
        data = {
            "waypointSymbol": waypoint,
        }
        resp = self.post(f"{self.api_url}/my/ships/{symbol}/navigate", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the destination is out of range, return the error payload.
            return resp.json()

    def refuel_ship(self, symbol: str, units: int=None, from_cargo: bool=False):
        """Refuel this ship from the local market. If not specifed, refuel to the maximum
        fuel capacity.
        """
        data = {"fromCargo": from_cargo}
        if units:
            data["units":units]

        resp = self.post(f"{self.api_url}/my/ships/{symbol}/refuel", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction failss, return the error payload.
            return resp.json()

    def sell_cargo(self, symbol: str, commodity: str, units: int):
        """Sell cargo for a given ship to a marketplace.
        """
        data = {
            "symbol": commodity,
            "units": units,
        }

        resp = self.post(f"{self.api_url}/my/ships/{symbol}/sell", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction failss, return the error payload.
            return resp.json()

    def purchase_cargo(self, symbol: str, commodity: str, units: int):
        """Purchase cargo for a given ship from a marketplace.
        """
        data = {
            "symbol": commodity,
            "units": units,
        }

        resp = self.post(f"{self.api_url}/my/ships/{symbol}/purchase", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction failss, return the error payload.
            return resp.json()

    # ----------------------------------------------------------------
    # Systems endpoints
    # ----------------------------------------------------------------
    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_systems(self):
        """List all system details
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        systems = []
        data = True

        while data:
            resp = self.get(f"{self.api_url}/systems", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                systems += data
                params["page"] += 1

        return systems

    def get_system(self, symbol: str):
        """Get the details for a single system.
        """
        resp = self.get(f"{self.api_url}/systems/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_waypoints(self, symbol: str, type: str=None, trait: str=None):
        """List all waypoints for the given system.
        """
        params = {
            "limit": 20,
            "page": 1,
        }
        if type:
            params["type"] = type
        if trait:
            params["traits"] = trait
        waypoints = []
        data = True

        while data:
            resp = self.get(
                f"{self.api_url}/systems/{symbol}/waypoints", params=params
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                waypoints += data
                params["page"] += 1

        return waypoints

    def get_waypoint(self, system_symbol: str, symbol: str):
        """Get a waypoint by symbol.
        """
        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_market(self, system_symbol: str, symbol: str):
        """Get a market for a waypoint.
        """
        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}/market")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_shipyard(self, system_symbol: str, symbol: str):
        """Get a shipyard for a waypoint.
        """
        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}/shipyard")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_jump_gate(self, system_symbol: str, symbol: str):
        """Get a jump gate for a waypoint.
        """
        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}/jump-gate")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_construction_site(self, system_symbol: str, symbol: str):
        """Get a construction site for a waypoint.
        """
        resp = self.get(f"{self.api_url}/systems/{system_symbol}/waypoints/{symbol}/construction")
        resp.raise_for_status()
        return resp.json()["data"]

    # TODO: supply_construction_site
