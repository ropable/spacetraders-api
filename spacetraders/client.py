from django.conf import settings
from ratelimit import limits, sleep_and_retry
from requests import Session
from .utils import infer_system_symbol


class Client(Session):
    """A Spacetraders HTTP client having methods named after each of the
    API endpoints. Derives the authentication token from the `API_TOKEN`
    environment variable.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers["Accept"] = "application/json"
        self.headers["Content-Type"] = "application/json"
        self.headers["Authorization"] = f"Bearer {settings.API_TOKEN}"

    def get_server_status(self):
        """Get server status.
        """
        resp = self.get(f"{settings.API_URL}/")
        resp.raise_for_status()
        return resp.json()

    def register_agent(self, symbol: str, email: str = None, faction: str = "COSMIC"):
        """Register a new player agent and return an authentication token.
        """
        # Remove the existing bearer token.
        self.headers.pop("Authorization")

        data = {
            "faction": faction,
            "symbol": symbol,
        }
        if email:
            data["email"] = email

        resp = self.post(f"{settings.API_URL}/register", json=data)
        resp.raise_for_status()
        data = resp.json()["data"]

        self.headers["Authorization"] = f"Bearer {data['token']}"
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
            resp = self.get(f"{settings.API_URL}/agents", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                agents += data
                params["page"] += 1

        return agents

    def get_agent(self):
        """Get the player agent's details from the game server.
        """
        resp = self.get(f"{settings.API_URL}/my/agent")
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
            resp = self.get(f"{settings.API_URL}/my/contracts", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                contracts += data
                params["page"] += 1

        return contracts

    def get_contract(self, contract_id: str):
        """Get a single contract's details.
        """
        resp = self.get(f"{settings.API_URL}/my/contracts/{contract_id}")
        resp.raise_for_status()
        return resp.json()["data"]

    def accept_contract(self, contract_id: str):
        """Accept a single contract.
        """
        resp = self.post(f"{settings.API_URL}/my/contracts/{contract_id}/accept")
        resp.raise_for_status()
        return resp.json()["data"]

    def deliver_cargo_to_contract(self, contract_id: str, ship_symbol: str, trade_symbol: str, units: int):
        """Deliver cargo to a contract.
        """
        data = {
            "shipSymbol": ship_symbol,
            "tradeSymbol": trade_symbol,
            "units": units,
        }
        resp = self.post(f"{settings.API_URL}/my/contracts/{contract_id}/deliver", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

    def fulfill_contract(self, contract_id: str):
        """Fulfill a contract.
        """
        resp = self.post(f"{settings.API_URL}/my/contracts/{contract_id}/accept")
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

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
            resp = self.get(f"{settings.API_URL}/factions", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                factions += data
                params["page"] += 1

        return factions

    def get_faction(self, symbol: str):
        """Fetch a single factions's details.
        """
        resp = self.get(f"{settings.API_URL}/factions/{symbol}")
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
            resp = self.get(f"{settings.API_URL}/my/ships", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                ships += data
                params["page"] += 1

        return ships

    def purchase_ship(self, waypoint_symbol: str, ship_type: str):
        """Purchase a ship of the given type from the given waypoint symbol.
        """
        data = {
            "shipType": ship_type,
            "waypointSymbol": waypoint_symbol,
        }

        resp = self.post(f"{settings.API_URL}/my/ships", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

    def get_ship(self, symbol: str):
        """Get the details of a single ship under the player's ownership.
        """
        resp = self.get(f"{settings.API_URL}/my/ships/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    def orbit_ship(self, symbol: str):
        """Attempt to move a ship into orbit.
        """
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/orbit")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_ship_cooldown(self, symbol: str):
        """Get the details of a ship's reactor cooldown.
        """
        resp = self.get(f"{settings.API_URL}/my/ships/{symbol}/cooldown")
        resp.raise_for_status()
        return resp.json()["data"]

    def dock_ship(self, symbol: str):
        """Attempt to dock a ship at the current location.
        """
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/dock")
        resp.raise_for_status()
        return resp.json()["data"]

    def extract_resources(self, symbol: str):
        """Extract resources from a waypoint into a ship.
        """
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/extract")
        resp.raise_for_status()
        return resp.json()["data"]

    def siphon_resources(self, symbol: str):
        """Siphon gas resources from a waypoint.
        """
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/siphon")
        resp.raise_for_status()
        return resp.json()["data"]

    def extract_resources_with_survey(self, symbol: str, survey: dict):
        """Extract resources from a waypoint into a ship.
        """
        data = {
            "survey": survey,
        }
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/extract/survey", json=data)
        resp.raise_for_status()
        return resp.json()["data"]

    def jettison_cargo(self, symbol: str, cargo_symbol: str, units: int):
        """Jettison the given cargo type from a ship.
        """
        data = {
            "symbol": cargo_symbol,
            "units": units,
        }
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/jettison", json=data)
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
        resp = self.patch(f"{settings.API_URL}/my/ships/{symbol}/nav", json=data)
        resp.raise_for_status()
        return resp.json()["data"]

    def navigate_ship(self, symbol: str, waypoint: str):
        """Attempt to navigate ship to the nominated waypoint.
        """
        data = {
            "waypointSymbol": waypoint,
        }
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/navigate", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the destination is out of range, return the error payload.
            return resp.json()

    def refuel_ship(self, symbol: str, units: int = None, from_cargo: bool = False):
        """Refuel this ship from the local market. If not specifed, refuel to the maximum
        fuel capacity.
        """
        data = {"fromCargo": from_cargo}
        if units:
            data["units":units]

        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/refuel", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

    def sell_cargo(self, symbol: str, trade_good: str, units: int):
        """Sell cargo for a given ship to a marketplace.
        """
        data = {
            "symbol": trade_good,
            "units": units,
        }

        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/sell", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

    def purchase_cargo(self, symbol: str, trade_good: str, units: int):
        """Purchase cargo for a given ship from a marketplace.
        """
        data = {
            "symbol": trade_good,
            "units": units,
        }

        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/purchase", json=data)
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
            # If the transaction fails, return the error payload.
            return resp.json()

    def negotiate_contract(self, symbol: str):
        """Negotiate a new contract with HQ."""
        resp = self.post(f"{settings.API_URL}/my/ships/{symbol}/negotiate/contract")
        try:
            resp.raise_for_status()
            return resp.json()["data"]
        except:
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
            resp = self.get(f"{settings.API_URL}/systems", params=params)
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                systems += data
                params["page"] += 1

        return systems

    def get_system(self, symbol: str):
        """Get the details for a single system.
        """
        resp = self.get(f"{settings.API_URL}/systems/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    @sleep_and_retry
    @limits(calls=30, period=60)
    def list_waypoints(self, symbol: str, type: str = None, trait: str = None):
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
                f"{settings.API_URL}/systems/{symbol}/waypoints", params=params
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            if data:
                waypoints += data
                params["page"] += 1

        return waypoints

    def get_waypoint(self, symbol: str, system_symbol: str = None):
        """Get a waypoint by symbol.
        """
        if not system_symbol:  # Infer the system symbol from the waypoint symbol.
            system_symbol = infer_system_symbol(symbol)
        resp = self.get(f"{settings.API_URL}/systems/{system_symbol}/waypoints/{symbol}")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_market(self, symbol: str, system_symbol: str = None):
        """Get a market for a waypoint.
        """
        if not system_symbol:  # Infer the system symbol from the waypoint symbol.
            system_symbol = infer_system_symbol(symbol)
        resp = self.get(f"{settings.API_URL}/systems/{system_symbol}/waypoints/{symbol}/market")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_shipyard(self, symbol: str, system_symbol: str = None):
        """Get a shipyard for a waypoint.
        """
        if not system_symbol:  # Infer the system symbol from the waypoint symbol.
            system_symbol = infer_system_symbol(symbol)
        resp = self.get(f"{settings.API_URL}/systems/{system_symbol}/waypoints/{symbol}/shipyard")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_jump_gate(self, symbol: str, system_symbol: str = None):
        """Get a jump gate for a waypoint.
        """
        if not system_symbol:  # Infer the system symbol from the waypoint symbol.
            system_symbol = infer_system_symbol(symbol)
        resp = self.get(f"{settings.API_URL}/systems/{system_symbol}/waypoints/{symbol}/jump-gate")
        resp.raise_for_status()
        return resp.json()["data"]

    def get_construction_site(self, symbol: str, system_symbol: str = None):
        """Get a construction site for a waypoint.
        """
        if not system_symbol:  # Infer the system symbol from the waypoint symbol.
            system_symbol = infer_system_symbol(symbol)
        resp = self.get(f"{settings.API_URL}/systems/{system_symbol}/waypoints/{symbol}/construction")
        resp.raise_for_status()
        return resp.json()["data"]

    # TODO: supply_construction_site
