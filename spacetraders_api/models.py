from datetime import datetime, timezone
from humanize import naturaldelta
from math import sqrt
from pydantic import BaseModel, Field
from threading import Timer
from typing import List, Any


class Ship(BaseModel):

    client: Any
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

    def get_waypoint(self):
        """Returns the waypoint where this ship is located.
        """
        return self.client.get_waypoint(self.nav["waypointSymbol"])

    def get_cooldown(self):
        """Returns the cooldown details of this ship, or None.
        """
        resp = self.client.get(f"{self.client.api_url}/my/ships/{self.symbol}/cooldown")
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()["data"]

    def in_range(self, waypoint) -> bool:
        """Returns True/False if the passed-in waypoint is within range of this ship.
        """
        current_waypoint = self.get_waypoint(self.client)
        distance = current_waypoint.distance(waypoint)
        if self.fuel["current"] > distance:
            return True
        else:
            return False

    def flight_mode(self, flight_mode: str):
        """Set the flight mode for this ship.
        """
        if flight_mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = {
            "flightMode": flight_mode,
        }
        resp = self.client.patch(f"{self.client.api_url}/my/ships/{self.symbol}/nav", json=data)
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data
        return self.nav

    def navigate(self, waypoint):
        """Navigate to the nominated waypoint, if within range.
        Passed-in `waypoint` can be a symbol or a Waypoint object.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/c766b84253edc-navigate-ship
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            self.orbit(self.client)

        # If the passed-in waypoint is a string, get the Waypoint object.
        if isinstance(waypoint, str):
            data = {
                "waypointSymbol": waypoint,
            }
        else:
            data = {
                "waypointSymbol": waypoint.symbol,
            }

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/navigate", json=data)
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

    def orbit(self):
        """Attempt to move this ship into orbit at the current location.
        """
        resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/orbit")
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data["nav"]
        return data

    def dock(self):
        """Dock this ship at the current location.
        """
        resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/dock")
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data["nav"]
        return data

    def sell_cargo(self, commodity: str, units: int):
        """Sell cargo in a given ship to a marketplace.
        TODO:
            - Persist transaction data.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b8ed791381b41-sell-cargo
        """
        # If not docked, do so first.
        if not self.nav["status"] == "DOCKED":
            self.dock()

        data = {
            "symbol": commodity,
            "units": units,
        }

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/sell", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            t = data["transaction"]
            print(f"Sold {t['units']} units of {t['tradeSymbol']} for {t['totalPrice']} credits")
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def refuel(self, units: int = None, from_cargo: bool = False):
        """Refuel this ship from the local market. If not specifed, refuel to the maximum
        fuel capacity.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/1bfb58c5239dd-refuel-ship
        """
        # If not docked, do so first.
        if not self.nav["status"] == "DOCKED":
            self.dock()

        data = {"fromCargo": from_cargo}
        if units:
            data["units": units]

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/refuel", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship fuel.
            self.fuel = data["fuel"]
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def survey(self) -> list:
        """Survey the current location.
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            self.orbit()

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/survey")
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cooldown.
            self.cooldown = data["cooldown"]
            # Print the cooldown expiry.
            exp = data["cooldown"]["expiration"]
            cooldown = datetime.fromisoformat(exp)
            now = datetime.now(timezone.utc)
            print(f"Ship cooldown ends in {naturaldelta(cooldown - now)} ({exp})")
            return data["surveys"]
        except:
            # Cooldown errors.
            return resp.json()

    def extract(self, survey: dict = None):
        """Extract resources from a waypoint into this ship.
        Calling extract() with a full cargo bay will not cause an exception, but will not
        extract any resources.

        Ref: https://spacetraders.stoplight.io/docs/spacetraders/b3931d097608d-extract-resources
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/cdf110a7af0ea-extract-resources-with-survey
        """
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            print("Entering orbit")
            self.orbit()

        try:
            if survey:
                resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/extract/survey", json=survey)
            else:
                resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/extract")
            resp.raise_for_status()
            data = resp.json()["data"]
            y = data["extraction"]["yield"]
            print(f"Extract yielded {y['units']} units of {y['symbol']}")
            # Update the ship's cargo status.
            self.cargo = data["cargo"]
            # Update the ship cooldown.
            self.cooldown = data["cooldown"]
            # Print the cooldown expiry.
            exp = data["cooldown"]["expiration"]
            cooldown = datetime.fromisoformat(exp)
            now = datetime.now(timezone.utc)
            print(f"Ship cooldown ends in {naturaldelta(cooldown - now)} ({exp})")
            return data
        except:
            # Cooldown errors.
            return resp.json()

    def extract_until_full(self, survey: dict = None):
        """Runs the extract() method, pausing between cooldowns, until the ship's cargo capacity
        is exhausted.
        """
        data = self.extract(survey)
        if self.cargo["capacity"] - self.cargo["units"] > 0:
            cooldown = datetime.fromisoformat(data["cooldown"]["expiration"])
            delay = cooldown - datetime.now(timezone.utc)
            timer = Timer(delay.seconds, self.extract_until_full, args=(survey,))
            print(f"Cargo capacity {self.cargo['units']}/{self.cargo['capacity']}, queuing the next extract in {delay.seconds} seconds")
            timer.start()
            return timer
        else:
            print("Ship cargo capacity is full")
            return

    def jettison_cargo(self, goods_symbol: str, units: int):
        """Jetison cargo.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/3b0f8b69f56ac-jettison-cargo
        """
        data = {
            "symbol": goods_symbol,
            "units": units,
        }

        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/jettison", json=data)
            resp.raise_for_status()
            print(f"Jettisoned {units} units of {goods_symbol}")
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            return data
        except:
            return resp.json()

    def refine(self, produce: str):
        data = {
            "produce": produce,
        }
        try:
            resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/refine", json=data)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            return data
        except:
            return resp.json()

    def find_market_imports(self, markets, exchange=False):
        """Print markets that import goods for the cargo inventory of this ship, given a passed-in
        list of market waypoints.
        """
        goods = [i["symbol"] for i in self.cargo["inventory"]]
        origin = self.get_waypoint()
        for m in markets:
            if not exchange:
                if any(good in m.imports for good in goods):
                    d = m.distance(origin)
                    print(m.symbol.ljust(12), m.type.ljust(19), "{:.2f}".format(d).ljust(6), ", ".join([i["symbol"] for i in m.market["imports"]]))
            else:
                if any(good in m.exchange for good in goods):
                    d = m.distance(origin)
                    print(m.symbol.ljust(12), m.type.ljust(19), "{:.2f}".format(d).ljust(6), ", ".join([i["symbol"] for i in m.market["exchange"]]))

    def find_trait(self, waypoints: list, trait: str):
        # For a given list of waypoints, output those having the given trait plus the distance
        # away from this ship.
        origin = self.get_waypoint()
        for wp in waypoints:
            if wp.has_trait(trait):
                d = wp.distance(origin)
                print(wp.symbol.ljust(12), wp.type.ljust(19), '{:.2f}'.format(d).ljust(6), ', '.join([t.symbol for t in wp.traits]))


class WaypointTrait(BaseModel):

    symbol: str
    name: str
    description: str

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol})"


class Waypoint(BaseModel):

    client: Any
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

    def get_market(self):
        """Retrieves import, export and exchange data for this waypoint if it has the
        MARKETPLACE trait, otherwise returns None.
        """
        if not self.has_trait("MARKETPLACE"):
            return None

        if self.market:
            return self.market  # Return cached data.

        resp = self.client.get(f"{self.client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/market")
        resp.raise_for_status()
        self.market = resp.json()["data"]
        return self.market

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
