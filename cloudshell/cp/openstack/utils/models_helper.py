from __future__ import annotations

import ipaddress


def get_port_range(port_str: str) -> tuple[int, int]:
    ports_str = port_str.split("-", 1)
    if len(ports_str) == 1:
        ports_str += ports_str
    ports_int = tuple(map(int, ports_str))
    min_ = min(ports_int)
    max_ = max(ports_int)
    return min_, max_


def is_cidr(cidr: str) -> bool:
    try:
        ipaddress.ip_network(cidr)
    except ValueError:
        return False
    else:
        return True
