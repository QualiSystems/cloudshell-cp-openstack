from __future__ import annotations

import ipaddress


def get_port_range(port_str: str) -> tuple[int, int]:
    ports = port_str.split("-", 1)
    if len(ports) == 1:
        ports += ports
    ports = tuple(map(int, ports))
    min_ = min(ports)
    max_ = max(ports)
    return min_, max_


def is_cidr(cidr: str) -> bool:
    try:
        ipaddress.ip_network(cidr)
    except ValueError:
        return False
    else:
        return True
