import requests
from dotenv import load_dotenv
import os
import time
from typing import Dict, Any, AnyStr, List


load_dotenv()
API_MY = 'https://api.spacetraders.io/v2/my'
API_SYSTEMS = f'https://api.spacetraders.io/v2/systems'


def get_auth_headers(token=None):
    if not token:
        token = os.environ.get('API_TOKEN')
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }


def get_agent() -> Dict[str, Any]:
    headers = get_auth_headers()
    resp = requests.get(API_MY + '/agent', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_ships() -> List:
    headers = get_auth_headers()
    resp = requests.get(API_MY + '/ships', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_ships_nav():
    """Return a list of all ships nav data.
    """
    ships_nav = []
    ships = get_ships()
    for ship in ships:
        symbol = {'symbol': ship['symbol']}
        ships_nav.append(symbol | ship['registration'] | ship['nav'])
    return ships_nav


def get_ship(ship: AnyStr) -> Dict[str, Any]:
    headers = get_auth_headers()
    resp = requests.get(API_MY + f'/ships/{ship}', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_contracts() -> List:
    headers = get_auth_headers()
    resp = requests.get(API_MY + '/contracts', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_system(system_sbl: AnyStr) -> Dict[str, Any]:
    headers = get_auth_headers()
    resp = requests.get(API_SYSTEMS + f'/{system_sbl}', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_system_waypoints(system_sbl: AnyStr) -> Dict[str, Any]:
    headers = get_auth_headers()
    resp = requests.get(API_SYSTEMS + f'/{system_sbl}/waypoints', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_system_imports(system_sbl):
    system = get_system(system_sbl)
    system_waypoint_symbols = [i['symbol'] for i in system['waypoints']]
    system_imports = {}
    for waypoint_sbl in system_waypoint_symbols:
        print(f'Getting for {waypoint_sbl}')
        try:
            market = get_market(system_sbl, waypoint_sbl)
            system_imports[waypoint_sbl] = [i['symbol'] for i in market['imports']]
        except:
            print('No market')
        time.sleep(0.75)
    return system_imports


def get_waypoint(system_sbl, waypoint_sbl):
    headers = get_auth_headers()
    resp = requests.get(API_SYSTEMS + f'/{system_sbl}/waypoints/{waypoint_sbl}', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_shipyard(system_sbl, waypoint_sbl):
    headers = get_auth_headers()
    resp = requests.get(API_SYSTEMS + f'/{system_sbl}/waypoints/{waypoint_sbl}/shipyard', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def get_market(system_sbl, waypoint_sbl):
    headers = get_auth_headers()
    resp = requests.get(API_SYSTEMS + f'/{system_sbl}/waypoints/{waypoint_sbl}/market', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


# TRANSACTION FUNCTIONS


def purchase_ship(ship_type, waypoint):
    headers = get_auth_headers()
    data = {
        "shipType": ship_type,
        "waypointSymbol": waypoint,
    }
    resp = requests.post(API_MY + '/ships', headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()['data']


def navigate_ship(ship, waypoint):
    headers = get_auth_headers()
    data = {
        "waypointSymbol": waypoint,
    }
    resp = requests.post(API_MY + f'/ships/{ship}/navigate', headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()['data']


def ship_action(ship, action):
    """`action`: dock, refuel, orbit, survey, extract
    """
    headers = get_auth_headers()
    resp = requests.post(API_MY + f'/ships/{ship}/{action}', headers=headers)
    resp.raise_for_status()
    return resp.json()['data']


def sell_cargo(ship, commodity, units):
    headers = get_auth_headers()
    data = {
        "symbol": commodity,
        "units": units,
    }
    resp = requests.post(API_MY + f'/ships/{ship}/sell', headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()['data']
