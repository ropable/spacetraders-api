from ratelimit import limits, sleep_and_retry
from spacetraders.utils import get_graph, depth_first_search
from galaxy.models import (
    Agent,
    Faction,
    FactionTrait,
    System,
    Waypoint,
    WaypointTrait,
    WaypointModifier,
    Ship,
    ShipNav,
    Contract,
    ContractDeliverGood,
    Market,
    Shipyard,
    MarketTradeGood,
)


@sleep_and_retry
@limits(calls=30, period=60)
def populate_factions(client):
    """Populate Faction instances from the server.
    """
    print("Downloading factions")
    factions = client.list_factions()

    for data in factions:
        if not Faction.objects.filter(symbol=data["symbol"]).exists():
            # Faction headquarters might be null.
            if data["headquarters"] and not System.objects.filter(symbol=data["headquarters"]).exists():
                print(f"Populating System {data['headquarters']}")
                system_data = client.get_system(data["headquarters"])
                headquarters = System.objects.create(
                    symbol=system_data["symbol"],
                    sector=system_data["sectorSymbol"],
                    type=system_data["type"],
                    x=system_data["x"],
                    y=system_data["y"],
                )
                print(f"{headquarters} system created")
            elif data["headquarters"] and System.objects.filter(symbol=data["headquarters"]).exists():
                headquarters = System.objects.get(symbol=data["headquarters"])
            else:
                headquarters = None

            if headquarters:
                for waypoint in system_data["waypoints"]:
                    if not Waypoint.objects.filter(symbol=waypoint["symbol"]).exists():
                        wp = Waypoint.objects.create(
                            symbol=waypoint["symbol"],
                            type=waypoint["type"],
                            x=waypoint["x"],
                            y=waypoint["y"],
                            system=headquarters,
                        )
                        print(f"{wp} waypoint created")

            faction = Faction.objects.create(
                symbol=data["symbol"],
                name=data["name"],
                description=data["description"],
                headquarters=headquarters,
                is_recruiting=data["isRecruiting"],
            )
            print(f"{faction} faction created")

            for trait in data["traits"]:
                if not FactionTrait.objects.filter(symbol=trait["symbol"]).exists():
                    new_trait = FactionTrait.objects.create(
                        symbol=trait["symbol"],
                        name=trait["name"],
                        description=trait["description"],
                    )
                    print(f"{new_trait} trait created")
                else:
                    new_trait = FactionTrait.objects.get(symbol=trait["symbol"])

                faction.traits.add(new_trait)
                print(f"{new_trait} trait added to {faction}")


@sleep_and_retry
@limits(calls=30, period=60)
def populate_system(client, system_symbol):
    """Populate a given system.
    """
    if not System.objects.filter(symbol=system_symbol).exists():
        system_data = client.get_system(system_symbol)
        system = System.objects.create(
            symbol=system_data["symbol"],
            sector=system_data["sectorSymbol"],
            type=system_data["type"],
            x=system_data["x"],
            y=system_data["y"],
        )
        print(f"{system} system created")
    else:
        system = System.objects.get(symbol=system_symbol)

    print(f"Downloading waypoints for {system}")
    waypoints = client.list_waypoints(system.symbol)
    # Sort waypoints by symbol.
    waypoints = sorted(waypoints, key=lambda x: x["symbol"])

    for waypoint_data in waypoints:
        if not Waypoint.objects.filter(symbol=waypoint_data["symbol"]).exists():
            waypoint = Waypoint.objects.create(
                symbol=waypoint_data["symbol"],
                type=waypoint_data["type"],
                system=system,
                x=waypoint_data["x"],
                y=waypoint_data["y"],
            )
            print(f"{waypoint} waypoint created")
        else:
            waypoint = Waypoint.objects.get(symbol=waypoint_data["symbol"])

        if "orbits" in waypoint_data and Waypoint.objects.filter(symbol=waypoint_data["orbits"]).exists():
            waypoint.orbits = Waypoint.objects.get(symbol=waypoint_data["orbits"])

        if "faction" in waypoint_data and Faction.objects.filter(symbol=waypoint_data["faction"]["symbol"]).exists():
            waypoint.faction = Faction.objects.get(symbol=waypoint_data["faction"]["symbol"])

        for trait in waypoint_data["traits"]:
            if not WaypointTrait.objects.filter(symbol=trait["symbol"]).exists():
                new_trait = WaypointTrait.objects.create(
                    symbol=trait["symbol"],
                    name=trait["name"],
                    description=trait["description"],
                )
                print(f"{new_trait} trait created")
            else:
                new_trait = WaypointTrait.objects.get(symbol=trait["symbol"])

            waypoint.traits.add(new_trait)
            print(f"{new_trait} trait added to {waypoint}")

        for modifier in waypoint_data["modifiers"]:
            if not WaypointModifier.objects.filter(symbol=modifier["symbol"]).exists():
                new_mod = WaypointModifier.objects.create(
                    symbol=modifier["symbol"],
                    name=modifier["name"],
                    description=modifier["description"],
                )
                print(f"{new_mod} modifier created")
            else:
                new_mod = WaypointModifier.objects.get(symbol=modifier["symbol"])

            waypoint.modifiers.add(new_mod)
            print(f"{new_mod} modifer added to {waypoint}")

    # Iterate through the data a second time, to fill any skipped attributes.
    for waypoint_data in waypoints:
        waypoint = Waypoint.objects.get(symbol=waypoint_data["symbol"])
        waypoint.update(waypoint_data)

    # Set certain waypoint types to orbit the system star.
    star = system.get_stars().first()
    for waypoint in Waypoint.objects.filter(system=system, type__in=["PLANET", "JUMP_GATE", "FUEL_STATION"]).exclude(orbits__isnull=False):
        waypoint.orbits = star
        waypoint.save()


def set_agent(client):
    """Save the player Agent to the database.
    """
    data = client.get_agent()
    if Faction.objects.filter(symbol=data["startingFaction"]).exists():
        starting_faction = Faction.objects.get(symbol=data["startingFaction"])
    else:
        starting_faction = None
    if not Agent.objects.filter(account_id=data["accountId"]).exists():
        agent = Agent.objects.create(
            account_id=data["accountId"],
            symbol=data["symbol"],
        )
    else:
        agent = Agent.objects.get(account_id=data["accountId"])

    agent.starting_faction = starting_faction
    agent.credits = data["credits"]
    agent.ship_count = data["shipCount"]
    if not agent.headquarters and Waypoint.objects.filter(symbol=data["headquarters"]).exists():
        agent.headquarters = Waypoint.objects.get(symbol=data["headquarters"])

    agent.save()
    return agent


@sleep_and_retry
@limits(calls=30, period=60)
def populate_ships(client):
    ships = client.list_ships()
    agent_data = client.get_agent()
    agent = Agent.objects.get(account_id=agent_data["accountId"])

    for data in ships:
        if not Ship.objects.filter(symbol=data["symbol"]).exists():
            ship = populate_ship(client, agent, data)
            print(f"Created {ship}")
        else:
            ship = Ship.objects.get(symbol=data["symbol"])
            ship.update(data)
            print(f"Refreshed data for {ship}")


def populate_ship(client, agent, data):
    if not System.objects.filter(symbol=data["nav"]["systemSymbol"]).exists():
        print(f"Populating System {data['nav']['systemSymbol']}")
        populate_system(client, data["nav"]["systemSymbol"])

    system = System.objects.get(symbol=data["nav"]["systemSymbol"])
    waypoint = Waypoint.objects.get(symbol=data["nav"]["waypointSymbol"])
    nav = ShipNav.objects.create(
        system=system,
        waypoint=waypoint,
        route=data["nav"]["route"],
        status=data["nav"]["status"],
        flight_mode=data["nav"]["flightMode"],
    )
    ship = Ship.objects.create(
        agent=agent,
        symbol=data["symbol"],
        registration=data["registration"],
        nav=nav,
        crew=data["crew"],
        frame=data["frame"],
        reactor=data["reactor"],
        engine=data["engine"],
        cooldown=data["cooldown"],
        cargo_capacity=data["cargo"]["capacity"],
        cargo_units=data["cargo"]["units"],
        fuel=data["fuel"],
    )
    ship.update(data)
    ship.update_cargo(data["cargo"])
    return ship


@sleep_and_retry
@limits(calls=30, period=60)
def populate_contracts(client):
    """Populate Contract instances from the game server.
    """
    print("Downloading contracts")
    contracts = client.list_contracts()
    agent_data = client.get_agent()
    agent = Agent.objects.get(account_id=agent_data["accountId"])

    for data in contracts:
        if not Contract.objects.filter(contract_id=data["id"]).exists():
            faction = Faction.objects.get(symbol=data["factionSymbol"])
            contract = Contract.objects.create(
                agent=agent,
                contract_id=data["id"],
                faction=faction,
                type=data["type"],
                terms_deadline=data["terms"]["deadline"],
                terms_payment=data["terms"]["payment"],
                accepted=data["accepted"],
                fulfilled=data["fulfilled"],
                expiration=data["expiration"],
                deadline_to_accept=data["deadlineToAccept"],
            )
            for good in data["terms"]["deliver"]:
                destination = Waypoint.objects.get(symbol=good["destinationSymbol"])
                ContractDeliverGood.objects.create(
                    contract=contract,
                    symbol=good["tradeSymbol"],
                    destination=destination,
                    units_required=good["unitsRequired"],
                    units_fulfilled=good["unitsFulfilled"],
                )
            print(f"{contract} created")
        else:
            contract = Contract.objects.get(contract_id=data["id"])
            contract.accepted = data["accepted"]
            contract.fulfilled = data["fulfilled"]
            contract.save()
            for good in data["deliver"]["deliver"]:
                deliver_good = ContractDeliverGood.objects.get(contract=contract, symbol=good["tradeSymbol"])
                deliver_good.units_fulfilled = good["unitsFulfilled"]
                deliver_good.save()
            print(f"{contract} updated")


@sleep_and_retry
@limits(calls=30, period=60)
def populate_markets(client):
    """Populate markets
    """
    market_waypoints = Waypoint.objects.filter(traits__in=WaypointTrait.objects.filter(symbol="MARKETPLACE"))

    for wp in market_waypoints:
        data = client.get_market(wp.symbol)
        market, created = Market.objects.get_or_create(waypoint=wp)
        market.update(data)
        print(f"Updated market {market}")


@sleep_and_retry
@limits(calls=30, period=60)
def populate_shipyards(client):
    shipyard_waypoints = Waypoint.objects.filter(traits__in=WaypointTrait.objects.filter(symbol="SHIPYARD"))

    for wp in shipyard_waypoints:
        data = client.get_shipyard(wp.symbol)
        shipyard, created = Shipyard.objects.get_or_create(waypoint=wp)
        shipyard.update(data)
        print(f"Updated shipyard {shipyard}")


def get_trade_pairs(system_symbol: str):
    """Return the set of all export/import pairs in a given system in the format:
        (
            (exporter waypoint symbol, importer waypoint symbol, trade good symbol, distance, spread, trade efficiency),
            ...
        )
    """
    market_tradegoods = MarketTradeGood.objects.filter(market__waypoint__system__symbol=system_symbol)
    paths = set()
    for exp in market_tradegoods.filter(type="EXPORT"):
        for imp in market_tradegoods.filter(type="IMPORT"):
            if imp.trade_good == exp.trade_good:
                exp.trade_matches.add(imp)
                distance = int(exp.market.waypoint.distance(imp.market.waypoint.coords))
                spread = imp.purchase_price - exp.sell_price
                paths.add((exp.market.waypoint.symbol, imp.market.waypoint.symbol, exp.trade_good.symbol, distance, spread, round(spread / distance, ndigits=1)))
    return sorted(paths)


def get_trade_routes(ship):
    """For a given starting waypoint, return the set of all trade routes for the system.
    Output:
        [
            (path_profit/unit, path_distance, [(export waypoint, import waypoint, trade good), ...]),
            ...
            ()
        ]
    """
    market_tradegoods = MarketTradeGood.objects.all()
    paths = set()
    for exp in market_tradegoods.filter(type="EXPORT"):
        for imp in market_tradegoods.filter(type="IMPORT"):
            if imp.trade_good == exp.trade_good:
                paths.add((exp.market.waypoint.symbol, imp.market.waypoint.symbol))
    paths = sorted(paths)
    graph = get_graph(paths)
    all_paths = depth_first_search(graph, ship.nav.waypoint.symbol)
    if not all_paths:  # Nil routes from the current location.
        return []
    max_len = max(len(p) for p in all_paths)
    # Analyze the longest group of paths only.
    analyze_paths = [p for p in all_paths if len(p) >= max_len - 2]
    trade_routes = []

    for path in analyze_paths:
        path_profit = 0
        path_distance = 0
        trade_route = []

        for k, symbol in enumerate(path[:-1]):
            best_profit = 0
            best_distance = 0
            for exp in market_tradegoods.filter(type="EXPORT"):
                for imp in market_tradegoods.filter(type="IMPORT"):
                    if imp.trade_good == exp.trade_good:
                        wp_ex = exp.market.waypoint
                        wp_im = imp.market.waypoint
                        if wp_ex.symbol == symbol and wp_im.symbol == path[k + 1]:
                            profit = imp.sell_price - exp.purchase_price
                            distance = int(wp_ex.distance(wp_im.coords))
                            if profit > best_profit:
                                best_profit = profit
                                best_distance = distance
                                best_trade = (wp_ex.symbol, wp_im.symbol, exp.trade_good.symbol)
            path_profit += best_profit
            path_distance += best_distance
            trade_route.append(best_trade)
        trade_routes.append((path_profit, path_distance, trade_route))

    return sorted(trade_routes, key=lambda x: x[0], reverse=True)
