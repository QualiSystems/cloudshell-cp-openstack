from __future__ import annotations

from typing import Generator

from novaclient.v2.servers import Server as NovaServer


def find_floating_ip(instance: NovaServer, mac: str) -> str | None:
    return next(_get_ips_of_instance(instance, mac, "floating"), None)


def find_fixed_ip(instance: NovaServer, mac: str) -> str | None:
    return next(_get_ips_of_instance(instance, mac, "fixed"), None)


def _get_ips_of_instance(
    instance: NovaServer, mac: str, type_: str, version: int = 4
) -> Generator[str, None, None]:
    instance.get()
    for net_name, addr_dicts in instance.addresses.items():
        for addr_dict in addr_dicts:
            if (
                addr_dict["OS-EXT-IPS-MAC:mac_addr"] == mac
                and addr_dict["OS-EXT-IPS:type"] == type_
                and addr_dict["version"] == version
            ):
                yield addr_dict["addr"]
