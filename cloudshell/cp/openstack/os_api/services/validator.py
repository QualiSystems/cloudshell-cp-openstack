from __future__ import annotations

import ipaddress
import random
from typing import TYPE_CHECKING, Iterable

import keystoneauth1.exceptions

from cloudshell.cp.openstack.os_api.models import NetworkType
from cloudshell.cp.openstack.resource_config import OSResourceConfig

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi


def validate_conf_and_connection(api: OsApi, resource_conf: OSResourceConfig) -> None:
    _validate_resource_conf(resource_conf)
    _validate_connection(api, resource_conf)
    _validate_network_attributes(api, resource_conf)


def _validate_resource_conf(resource_conf: OSResourceConfig) -> None:
    _is_not_empty(resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url)
    _is_http_url(resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url)

    _is_not_empty(resource_conf.os_domain_name, resource_conf.ATTR_NAMES.os_domain_name)
    _is_not_empty(
        resource_conf.os_project_name, resource_conf.ATTR_NAMES.os_project_name
    )
    _is_not_empty(resource_conf.user, resource_conf.ATTR_NAMES.user)
    _is_not_empty(resource_conf.password, resource_conf.ATTR_NAMES.password)
    _is_not_empty(resource_conf.os_mgmt_net_id, resource_conf.ATTR_NAMES.os_mgmt_net_id)
    _is_not_empty(
        resource_conf.floating_ip_subnet_id,
        resource_conf.ATTR_NAMES.floating_ip_subnet_id,
    )
    _is_one_of_the(
        resource_conf.vlan_type, ("VLAN", "VXLAN"), resource_conf.ATTR_NAMES.vlan_type
    )


def _is_not_empty(value: str, attr_name: str) -> None:
    if not value:
        raise ValueError(f"{attr_name} cannot be empty")


def _is_http_url(value: str, attr_name: str) -> None:
    v = value.lower()
    if not v.startswith("http://") and not v.startswith("https://"):
        raise ValueError(f"{value} is not valid format for {attr_name}")


def _is_one_of_the(value: str, expected_vals: Iterable[str], attr_name: str) -> None:
    if value.lower() not in map(str.lower, expected_vals):
        raise ValueError(f"{attr_name} should be one of {expected_vals}")


def _validate_connection(api: OsApi, resource_conf: OSResourceConfig) -> None:
    try:
        list(api.Instance.all())
    except (
        keystoneauth1.exceptions.http.BadRequest,
        keystoneauth1.exceptions.http.Unauthorized,
    ):
        raise
    except keystoneauth1.exceptions.http.NotFound:
        raise ValueError(f"Controller URL {resource_conf.controller_url} is not found")
    except Exception as e:
        raise ValueError(f"One or more values are not correct. {e}") from e


def _validate_network_attributes(api: OsApi, resource_conf: OSResourceConfig) -> None:
    _get_network_dict(api, resource_conf.os_mgmt_net_id)
    _validate_floating_ip_subnet(api, resource_conf.floating_ip_subnet_id)
    _validate_vlan_type(
        api, resource_conf.vlan_type, resource_conf.os_physical_int_name
    )
    _validate_reserved_networks(resource_conf.os_reserved_networks)


def _get_network_dict(api: OsApi, network_id: str) -> None:
    api.Network.get(network_id)


def _validate_floating_ip_subnet(api: OsApi, floating_ip_subnet_id: str) -> None:
    subnet = api.Subnet.get(floating_ip_subnet_id)
    network = subnet.network
    if not network.is_external:
        msg = f"The {network} is not an external network"
        raise ValueError(msg)


def _validate_vlan_type(api: OsApi, vlan_type: str, os_physical_int: str) -> None:
    vlan_id = _get_free_vlan_id(api)
    net = api.Network.create(
        "qs_autoload_validation_net",
        network_type=NetworkType(vlan_type),
        vlan_id=vlan_id,
        physical_iface_name=os_physical_int,
    )
    net.remove()


def _get_free_vlan_id(api: OsApi) -> int:
    used_vlans = {net.vlan_id for net in api.Network.all() if net.vlan_id}

    vlan_id = random.randint(100, 4000)
    while vlan_id in used_vlans:
        vlan_id = random.randint(100, 4000)

    return vlan_id


def _validate_reserved_networks(reserved_networks: list[str]):
    for net in reserved_networks:
        # Just try to create an IPv4Network if anything, it'd raise a ValueError
        ipaddress.ip_network(net)
