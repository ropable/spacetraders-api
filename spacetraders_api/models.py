from datetime import datetime, timezone
from humanize import naturaldelta
from math import sqrt
from pydantic import BaseModel, Field
from typing import List, Any


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

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol}, {self.frame['symbol']}, {self.registration['role']})"

    def get_waypoint(self, client):
        """Returns the waypoint where this ship is located.
        """
        return client.get_waypoint(self.nav["waypointSymbol"])

    def in_range(self, client, waypoint) -> bool:
        """Returns True/False if the passed-in waypoint is within range of this ship.
        """
        current_waypoint = self.get_waypoint(client)
        distance = current_waypoint.distance(waypoint)
        if self.fuel["current"] > distance:
            return True
        else:
            return False

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
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data
        return self.nav

    def navigate(self, client, waypoint):
        """Navigate to the nominated waypoint, if within range.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/c766b84253edc-navigate-ship
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            self.orbit(client)

        data = {
            "waypointSymbol": waypoint.symbol,
        }
        try:
            resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/navigate", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship fuel and nav status.
            self.fuel = data["fuel"]
            self.nav = data["nav"]
            now = datetime.now(timezone.utc)
            arrival = datetime.fromisoformat(self.nav["route"]["arrival"])
            print(f"Estimated arrival in {naturaldelta(arrival - now)}")
            return self.nav
        except:
            # If the destination is out of range, return the error payload.
            return resp.json()

    def orbit(self, client):
        """Attempt to move this ship into orbit at the current location.
        """
        resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/orbit")
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data["nav"]
        return data

    def dock(self, client):
        """Dock this ship at the current location.
        """
        resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/dock")
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data["nav"]
        return data

    def sell_cargo(self, client, commodity: str, units: int):
        """Sell cargo in a given ship to a marketplace.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b8ed791381b41-sell-cargo
        """
        # If not docked, do so first.
        if not self.nav["status"] == "DOCKED":
            self.dock(client)

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
        """Refuel this ship from the local market. If not specifed, refuel to the maximum
        fuel capacity.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/1bfb58c5239dd-refuel-ship
        """
        # If not docked, do so first.
        if not self.nav["status"] == "DOCKED":
            self.dock(client)

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
        """
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            self.orbit(client)

        return

    def extract(self, client, survey: dict = None):
        """Extract resources from a waypoint into this ship.
        Calling extract() with a full cargo bay will not cause an exception, but will not
        extract any resources.

        TODO:
            - Accept survey in request body.

        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b3931d097608d-extract-resources
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            print("Entering orbit")
            self.orbit(client)

        try:
            resp = client.post(f"{client.api_url}/my/ships/{self.symbol}/extract")
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship's cargo status.
            self.cargo = data["cargo"]
            # Print the cooldown expiry.
            exp = data["cooldown"]["expiration"]
            cooldown = datetime.fromisoformat(exp)
            now = datetime.now(timezone.utc)
            print(f"Ship cooldown ends in {naturaldelta(cooldown - now)} ({exp})")

            return data["extraction"]
        except:
            # Cooldown errors.
            return resp.json()

    def find_market_imports(self, client, markets, exchange=False):
        """Print markets that import goods for the cargo inventory of this ship, given a passed-in
        list of market waypoints.
        """
        goods = [i["symbol"] for i in self.cargo["inventory"]]
        origin = self.get_waypoint(client)
        for m in markets:
            if not exchange:
                if any(good in m.imports for good in goods):
                    d = m.distance(origin)
                    print(m.symbol.ljust(12), m.type.ljust(19), "{:.2f}".format(d).ljust(6), ", ".join([i["symbol"] for i in m.market["imports"]]))
            else:
                if any(good in m.exchange for good in goods):
                    d = m.distance(origin)
                    print(m.symbol.ljust(12), m.type.ljust(19), "{:.2f}".format(d).ljust(6), ", ".join([i["symbol"] for i in m.market["exchange"]]))


class WaypointTrait(BaseModel):

    symbol: str
    name: str
    description: str

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol})"


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

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol}, {self.type})"

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

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol})"
