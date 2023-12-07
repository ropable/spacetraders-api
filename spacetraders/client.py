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
        """Get a single agent's details from the game server.
        """
        resp = self.get(f"{self.api_url}/my/agent")
        resp.raise_for_status()
        return resp.json()["data"]

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_contracts(self):
        """List all contract details.
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

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_ships(self):
        """List all of the ships under your ownership.
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
        """Get the details of a single ship under your ownership.
        """
        resp = self.get(f"{self.api_url}/my/ships/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]
