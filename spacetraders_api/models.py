from datetime import datetime, timezone
from humanize import naturaldelta
from math import dist
import os
from pydantic import BaseModel, Field
from threading import Timer
from typing import List, Any
from zoneinfo import ZoneInfo


tz = os.environ.get("TZ", "Australia/Perth")
TZ = ZoneInfo(tz)


class Ship(BaseModel):
    symbol: str = Field(alias="symbol", default=None)
    registration: dict = Field(alias="registration", default={})
    nav: dict = Field(alias="nav", default={})
    crew: dict = Field(alias="crew", default={})
    frame: dict = Field(alias="frame", default={})
    reactor: dict = Field(alias="reactor", default={})
    engine: dict = Field(alias="engine", default={})
    cooldown: dict = Field(alias="cooldown", default={})
    modules: List[dict] = Field(alias="modules", default=[])
    mounts: List[dict] = Field(alias="mounts", default=[])
    cargo: dict = Field(alias="cargo", default={})
    fuel: dict = Field(alias="fuel", default={})

    client: Any

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol}, {self.frame['symbol']}, {self.registration['role']})"

    def get_waypoint(self):
        """Returns the waypoint where this ship is located."""
        return self.client.get_waypoint(self.nav["waypointSymbol"])

    def get_cooldown(self):
        """Returns the cooldown details of this ship, or None."""
        resp = self.client.get(f"{self.client.api_url}/my/ships/{self.symbol}/cooldown")
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()["data"]

    def flight_mode(self, flight_mode: str):
        """Set the flight mode for this ship."""
        if flight_mode not in ["DRIFT", "STEALTH", "CRUISE", "BURN"]:
            return None

        data = {
            "flightMode": flight_mode,
        }
        resp = self.client.patch(
            f"{self.client.api_url}/my/ships/{self.symbol}/nav", json=data
        )
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
            self.orbit()

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
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/navigate", json=data
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship fuel and nav status.
            self.fuel = data["fuel"]
            self.nav = data["nav"]
            self.arrival()  # Print the arrival time.
            return self.nav
        except:
            # If the destination is out of range, return the error payload.
            return resp.json()

    def orbit(self):
        """Attempt to move this ship into orbit at the current location."""
        resp = self.client.post(f"{self.client.api_url}/my/ships/{self.symbol}/orbit")
        resp.raise_for_status()
        data = resp.json()["data"]
        # Update the ship nav status.
        self.nav = data["nav"]
        return data

    def dock(self):
        """Dock this ship at the current location."""
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
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/sell", json=data
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            t = data["transaction"]
            print(
                f"Sold {t['units']} units of {t['tradeSymbol']} for {t['totalPrice']} credits"
            )
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
            data["units":units]

        try:
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/refuel", json=data
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship fuel.
            self.fuel = data["fuel"]
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def survey(self) -> list:
        """Survey the current location."""
        # If not in orbit, do so first.
        if not self.nav["status"] == "IN_ORBIT":
            self.orbit()

        try:
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/survey"
            )
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
                resp = self.client.post(
                    f"{self.client.api_url}/my/ships/{self.symbol}/extract/survey",
                    json=survey,
                )
            else:
                resp = self.client.post(
                    f"{self.client.api_url}/my/ships/{self.symbol}/extract"
                )
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
            print(
                f"Cargo capacity {self.cargo['units']}/{self.cargo['capacity']}, queuing the next extract in {delay.seconds} seconds"
            )
            timer.start()
            return timer
        else:
            print("Ship cargo capacity is full")
            return

    def jettison_cargo(self, goods_symbol: str, units: int = None):
        """Jettison cargo. If `units` is not specified, jettison the full amount of that cargo.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/3b0f8b69f56ac-jettison-cargo
        """
        if not units:
            for i in self.cargo["inventory"]:
                if i["symbol"] == goods_symbol:
                    units = i["units"]
                    break

        if not units:
            return

        data = {
            "symbol": goods_symbol,
            "units": units,
        }

        try:
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/jettison", json=data
            )
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
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/refine", json=data
            )
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
                    print(
                        m.symbol.ljust(12),
                        m.type.ljust(19),
                        "{:.2f}".format(d).ljust(6),
                        ", ".join([i["symbol"] for i in m.market["imports"]]),
                    )
            else:
                if any(good in m.exchange for good in goods):
                    d = m.distance(origin)
                    print(
                        m.symbol.ljust(12),
                        m.type.ljust(19),
                        "{:.2f}".format(d).ljust(6),
                        ", ".join([i["symbol"] for i in m.market["exchange"]]),
                    )

    def find_trait(self, waypoints: list, trait: str):
        # For a given list of waypoints, output those having the given trait plus the distance
        # away from this ship.
        origin = self.get_waypoint()
        for wp in waypoints:
            if wp.has_trait(trait):
                d = wp.distance(origin)
                print(
                    wp.symbol.ljust(12),
                    wp.type.ljust(19),
                    "{:.2f}".format(d).ljust(6),
                    ", ".join([t.symbol for t in wp.traits]),
                )

    def purchase_cargo(self, commodity: str, units: int):
        """Purchase cargo in a given ship from a marketplace.
        TODO:
            - Persist transaction data.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/45acbf7dc3005-purchase-cargo
        """
        # If not docked, do so first.
        if not self.nav["status"] == "DOCKED":
            self.dock()

        data = {
            "symbol": commodity,
            "units": units,
        }

        try:
            resp = self.client.post(
                f"{self.client.api_url}/my/ships/{self.symbol}/purchase", json=data
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            # Update the ship cargo.
            self.cargo = data["cargo"]
            t = data["transaction"]
            print(
                f"Purchased {t['units']} units of {t['tradeSymbol']} for {t['totalPrice']} credits"
            )
            # Return the transaction output.
            return data["transaction"]
        except:
            return resp.json()

    def arrival(self):
        if self.nav["status"] != "IN_TRANSIT":
            return
        now = datetime.now(timezone.utc)
        arrival = datetime.fromisoformat(self.nav["route"]["arrival"])
        print(
            f"Arrival in {naturaldelta(arrival - now)} ({arrival.astimezone(TZ).strftime('%d/%m/%Y %H:%M')})"
        )


class WaypointTrait(BaseModel):
    symbol: str = Field(alias="symbol", default=None)
    name: str = Field(alias="name", default=None)
    description: str = Field(alias="description", default=None)

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol})"


class Waypoint(BaseModel):
    symbol: str = Field(alias="symbol", default=None)
    type: str = Field(alias="type", default=None)
    system_symbol: str = Field(alias="systemSymbol", default=None)
    x: int = Field(alias="x", default=None)
    y: int = Field(alias="y", default=None)
    orbitals: List = Field(alias="orbitals", default=[])
    orbits: str = Field(alias="orbits", default=None)
    faction: dict = Field(alias="faction", default={})
    traits: List["WaypointTrait"] = Field(alias="traits", default=[])
    modifiers: List = Field(alias="modifiers", default=[])
    chart: dict = Field(alias="chart", default={})
    is_under_construction: Any = Field(alias="isUnderConstruction", default=None)

    client: Any = Field(alias="client", default=None)
    market: dict = Field(alias="market", default={})
    # TODO: market info age / expiry.
    jump_gate_connections: List[str] = Field(alias="jump_gate_connections", default=[])
    construction_site: dict = Field(alias="construction_site", default={})

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol}, {self.type})"

    @property
    def coords(self):
        """Return the x, y coordinates of this waypoint as a tuple."""
        return (self.x, self.y)

    def has_trait(self, symbol: str):
        """Returns boolean based on whether this waypoint has the given trait symbol."""
        for trait in self.traits:
            if trait.symbol == symbol:
                return True

        return False

    def distance(self, waypoint):
        """Calculate the distance from this waypoint to the passed-in waypoint."""
        return dist((self.x, self.y), (waypoint.x, waypoint.y))

    def get_market(self):
        """Retrieves import, export and exchange data for this waypoint if it has the
        MARKETPLACE trait, otherwise returns None.
        """
        if not self.has_trait("MARKETPLACE"):
            return None

        resp = self.client.get(
            f"{self.client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/market"
        )
        resp.raise_for_status()
        self.market = resp.json()["data"]
        return self.market

    def get_shipyard(self):
        """Retrieves shipyard data from this waypoint if it has the SHIPYARD trait,
        otherwise returns None.
        """
        if not self.has_trait("SHIPYARD"):
            return None

        resp = self.client.get(
            f"{self.client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/shipyard"
        )
        resp.raise_for_status()
        return resp.json()["data"]

    @property
    def imports(self):
        """Returns a comma-separated sting of imports."""
        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["imports"]])

    @property
    def exports(self):
        """Returns a comma-separated sting of exports."""
        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["exports"]])

    @property
    def exchange(self):
        """Returns a comma-separated sting of exchange goods."""
        if not self.market:
            return None

        return ", ".join([i["symbol"] for i in self.market["exchange"]])

    def get_jump_gate(self):
        """Retrieves jump gate details for this waypoint if type JUMP_GATE,
        otherwise returns None.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/decd101af6414-get-jump-gate
        """
        if not self.type == "JUMP_GATE":
            return None

        resp = self.client.get(
            f"{self.client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/jump-gate"
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        self.jump_gate_connections = data["connections"]
        return self.jump_gate_connections

    def get_construction_site(self):
        """Retrieves construction details for this waypoint if it has the
        property is_under_construction = True, otherwise returns None.
        Ref: https://spacetraders.stoplight.io/docs/spacetraders/c4db8d0c02144-get-construction-site
        """
        if not self.is_under_construction:
            return None

        resp = self.client.get(
            f"{self.client.api_url}/systems/{self.system_symbol}/waypoints/{self.symbol}/construction"
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        self.construction_site = data
        return self.construction_site


class System(BaseModel):
    symbol: str = Field(alias="symbol", default=None)
    sector_symbol: str = Field(alias="sectorSymbol", default=None)
    type: str = Field(alias="type", default=None)
    x: int = Field(alias="x", default=None)
    y: int = Field(alias="y", default=None)
    waypoints: List = Field(alias="waypoints", default=[])
    factions: List = Field(alias="factions", default=[])

    def __repr__(self):
        cls = self.__class__.__name__
        return f"{cls} ({self.symbol})"
