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
    ShipMount,
    ShipModule,
    CargoType,
    ShipCargoItem,
    Contract,
    ContractDeliverGood,
    Market,
    TradeGood,
    Transaction,
    MarketTradeGood,
)


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


def populate_ships(client):
    ships = client.list_ships()
    agent_data = client.get_agent()
    agent = Agent.objects.get(account_id=agent_data["accountId"])

    for data in ships:
        if not Ship.objects.filter(symbol=data["symbol"]).exists():
            # Check that system exists in the database.
            if not System.objects.filter(symbol=data["nav"]["systemSymbol"]).exists():
                # Populate the system
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
            print(f"Created {ship}")
        else:
            ship = Ship.objects.get(symbol=data["symbol"])
            ship.crew = data["crew"]
            ship.frame = data["frame"]
            ship.reactor = data["reactor"]
            ship.engine = data["engine"]
            ship.cooldown = data["cooldown"]
            ship.cargo_capacity = data["cargo"]["capacity"]
            ship.cargo_units = data["cargo"]["units"]
            ship.fuel = data["fuel"]
            ship.save()

            # Update ship.nav
            nav = ship.nav
            nav.system = System.objects.get(symbol=data["nav"]["systemSymbol"])
            nav.waypoint = Waypoint.objects.get(symbol=data["nav"]["waypointSymbol"])
            nav.route = data["nav"]["route"]
            nav.status = data["nav"]["status"]
            nav.flight_mode = data["nav"]["flightMode"]
            nav.save()

        ship.modules.clear()
        for module_data in data["modules"]:
            if not ShipModule.objects.filter(symbol=module_data["symbol"]).exists():
                module = ShipModule(
                    symbol=module_data["symbol"],
                    name=module_data["name"],
                    description=module_data["description"],
                )
                if "capacity" in module_data:
                    module.capacity = module_data["capacity"]
                if "range" in module_data:
                    module.range = module_data["range"]
                if "requirements" in module_data:
                    module.requirements = module_data["requirements"]
                module.save()
            else:
                module = ShipModule.objects.get(symbol=module_data["symbol"])
            ship.modules.add(module)

        ship.mounts.clear()
        for mount_data in data["mounts"]:
            if not ShipMount.objects.filter(symbol=mount_data["symbol"]).exists():
                mount = ShipMount(
                    symbol=mount_data["symbol"],
                    name=mount_data["name"],
                    description=mount_data["description"],
                )
                if "strength" in mount_data:
                    mount.strength = mount_data["strength"]
                if "deposits" in mount_data:
                    mount.deposits = mount_data["deposits"]
                if "requirements" in mount_data:
                    mount.requirements = mount_data["requirements"]
                mount.save()
            else:
                mount = ShipMount.objects.get(symbol=mount_data["symbol"])
            ship.mounts.add(mount)

        for good in data["cargo"]["inventory"]:
            if not CargoType.objects.filter(symbol=good["symbol"]).exists():
                cargo_type = CargoType.objects.create(
                    symbol=good["symbol"],
                    name=good["name"],
                    description=good["description"],
                )
            else:
                cargo_type = CargoType.objects.get(symbol=good["symbol"])

            # New inventory good.
            if not ShipCargoItem.objects.filter(type=cargo_type, ship=ship).exists():
                item = ShipCargoItem.objects.create(
                    type=cargo_type,
                    ship=ship,
                    units=good["units"],
                )
            elif ShipCargoItem.objects.filter(type=cargo_type, ship=ship).exists():
                # Update the number of units if required.
                item = ShipCargoItem.objects.get(type=cargo_type, ship=ship)
                if item.units != good["units"]:
                    item.units = good["units"]
                    item.save()

            # Check the set of ship cargo items. If there is anything not currently in inventory,
            # zero out the balance.
            current_cargo = CargoType.objects.filter(symbol__in=[good["symbol"] for good in data["cargo"]["inventory"]])
            not_held = ShipCargoItem.objects.filter(ship=ship).exclude(type__in=current_cargo)
            for item in not_held:
                item.units = 0
                item.save()

        print(f"Refreshed data for {ship}")


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


def populate_markets(client):
    """Populate markets
    """
    market_waypoints = Waypoint.objects.filter(traits__in=WaypointTrait.objects.filter(symbol='MARKETPLACE'))

    for wp in market_waypoints:
        data = client.get_market(wp.system.symbol, wp.symbol)
        market, created = Market.objects.get_or_create(waypoint=wp)

        for imp in data["imports"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=imp["symbol"],
                name=imp["name"],
                description=imp["description"],
            )
            market.imports.add(trade_good)

        for exp in data["exports"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=exp["symbol"],
                name=exp["name"],
                description=exp["description"],
            )
            market.exports.add(trade_good)

        for ex in data["exchange"]:
            trade_good, created = TradeGood.objects.get_or_create(
                symbol=ex["symbol"],
                name=ex["name"],
                description=ex["description"],
            )
            market.exchange.add(trade_good)

        if "transactions" in data:
            for trans in data["transactions"]:
                # FIXME: we assume that the TradeGood exists at this point.
                trade_good = TradeGood.objects.get(symbol=trans["tradeSymbol"])
                transaction, created = Transaction.objects.get_or_create(
                    market=market,
                    ship_symbol=trans["shipSymbol"],
                    trade_good=trade_good,
                    type=trans["type"],
                    units=trans["units"],
                    price_per_unit=trans["pricePerUnit"],
                    total_price=trans["totalPrice"],
                    timestamp=trans["timestamp"],
                )

        if "tradeGoods" in data:
            for good in data["tradeGoods"]:
                trade_good = TradeGood.objects.get(symbol=good["symbol"])
                if not MarketTradeGood.objects.filter(market=market, trade_good=trade_good, type=good["type"]).exists():
                    market_trade_good = MarketTradeGood(
                        market=market,
                        trade_good=trade_good,
                        type=good["type"],
                    )
                else:
                    market_trade_good = MarketTradeGood.objects.get(market=market, trade_good=trade_good, type=good["type"])

                market_trade_good.trade_volume = good["tradeVolume"]
                market_trade_good.supply = good["supply"]
                market_trade_good.purchase_price = good["purchasePrice"]
                market_trade_good.sell_price = good["sellPrice"]
                if "activity" in good:  # Type EXCHANGE goods have no activity
                    market_trade_good.activity = good["activity"]

        print(f"Updated market {market}")
