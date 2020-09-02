import ipaddress
from itertools import chain
from typing import Generator, Optional

from novaclient.v2.servers import Server as NovaServer


def _get_ips_of_instance(
    instance: NovaServer, type_: str, net_name: Optional[str] = None
) -> Generator[str, None, None]:
    if net_name is not None:
        addresses = instance.addresses.get(net_name, [])
    else:
        addresses = chain.from_iterable(instance.addresses.values())

    for address_dict in addresses:
        if address_dict["OS-EXT-IPS:type"] == type_:
            yield address_dict["addr"]


def get_floating_ip(instance: NovaServer) -> str:
    return next(_get_ips_of_instance(instance, "floating"), "")


def get_private_ip(instance: NovaServer, net_name: str) -> str:
    ip = ""
    for ip in _get_ips_of_instance(instance, "fixed", net_name):
        if isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address):
            break
    return ip
