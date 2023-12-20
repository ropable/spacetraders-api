from collections import defaultdict
from datetime import datetime, timezone


def sleep_until(arrival: datetime, buffer: int = 1):
    """Return the number of seconds until the nominated datetime is reached (plus `buffer`),
    or None if the datetime is in the past.
    """
    now = datetime.now(timezone.utc)
    if arrival <= now:
        return None
    pause = (arrival - now).seconds + buffer
    return pause


def infer_system_symbol(waypoint_symbol):
    """Infer the System symbol from a passed-in Waypoint symbol.
    """
    return "-".join(waypoint_symbol.split("-")[0:-1])


def get_graph(paths):
    graph = defaultdict(set)
    for (start, finish) in paths:
        graph[start].add(finish)

    return graph


def depth_first_search(graph, v, seen=None, path=None):
    if seen is None:
        seen = []
    if path is None:
        path = [v]

    seen.append(v)
    paths = []

    for t in graph[v]:
        if t not in seen:
            t_path = path + [t]
            paths.append(tuple(t_path))
            paths.extend(depth_first_search(graph, t, seen[:], t_path))

    return paths
