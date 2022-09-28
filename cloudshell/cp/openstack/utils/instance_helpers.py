from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.openstack.exceptions import MgmtIfaceIsMissed

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.models import Instance, Interface, SecurityGroup


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


def get_mgmt_iface_name(inst: Instance) -> str:
    return "mgmt-port"


def get_mgmt_iface(inst: Instance) -> Interface:
    port_name = get_mgmt_iface_name(inst)
    iface = inst.find_interface_by_port_name(port_name)
    if not iface:
        raise MgmtIfaceIsMissed(inst)
    return iface


def get_instance_security_group_name(inst: Instance) -> str:
    return f"sg-{inst.name}"


def get_instance_security_group(inst: Instance) -> SecurityGroup | None:
    name = get_instance_security_group_name(inst)
    sg = inst.find_security_group(name)
    return sg
