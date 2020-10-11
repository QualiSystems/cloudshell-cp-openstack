import ipaddress
import random
from typing import TYPE_CHECKING, Iterable, List

import keystoneauth1.exceptions
from neutronclient.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.resource_config import OSResourceConfig

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OSApi


def validate_conf_and_connection(api: "OSApi", resource_conf: OSResourceConfig):
    _validate_resource_conf(resource_conf)
    _validate_connection(api, resource_conf)
    _validate_network_attributes(api, resource_conf)


def _validate_resource_conf(resource_conf: OSResourceConfig):
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


def _is_not_empty(value: str, attr_name: str):
    if not value:
        raise ValueError(f"{attr_name} cannot be empty")


def _is_http_url(value: str, attr_name: str):
    v = value.lower()
    if not v.startswith("http://") and not v.startswith("https://"):
        raise ValueError(f"{value} is not valid format for {attr_name}")


def _is_one_of_the(value: str, expected_vals: Iterable[str], attr_name: str):
    if value.lower() not in map(str.lower, expected_vals):
        raise ValueError(f"{attr_name} should be one of {expected_vals}")


def _validate_connection(api: "OSApi", resource_conf: OSResourceConfig):
    try:
        api._nova.servers.list()
    except (
        keystoneauth1.exceptions.http.BadRequest,
        keystoneauth1.exceptions.http.Unauthorized,
    ):
        raise
    except keystoneauth1.exceptions.http.NotFound:
        raise ValueError(f"Controller URL {resource_conf.controller_url} is not found")
    except Exception as e:
        raise ValueError(f"One or more values are not correct. {e}") from e


def _validate_network_attributes(api: "OSApi", resource_conf: OSResourceConfig):
    _get_network_dict(api, resource_conf.os_mgmt_net_id)
    _validate_floating_ip_subnet(api, resource_conf.floating_ip_subnet_id)
    _validate_vlan_type(
        api, resource_conf.vlan_type, resource_conf.os_physical_int_name
    )
    _validate_reserved_networks(resource_conf.os_reserved_networks)


def _get_network_dict(api: "OSApi", network_id: str):
    try:
        val = api.get_network_dict(id=network_id)
    except Exception as e:
        raise ValueError(f"Error getting network. {e}") from e
    return val


def _validate_floating_ip_subnet(api: "OSApi", floating_ip_subnet_id: str):
    net_id = api.get_network_id_for_subnet_id(floating_ip_subnet_id)
    ext_net = _get_network_dict(api, net_id)
    if not ext_net["router:external"]:
        msg = f"Network with ID {net_id} exists but is not an external network"
        raise ValueError(msg)


def _validate_vlan_type(api: "OSApi", vlan_type: str, os_physical_int: str):
    e_msg = ""
    for retry in range(1, 11):
        data = {
            "provider:network_type": vlan_type.lower(),
            "name": "qs_autoload_validation_net",
            "provider:segmentation_id": random.randint(100, 4000),
            "admin_state_up": True,
        }
        if vlan_type.lower() == "vlan":
            data["provider:physical_network"] = os_physical_int
        try:
            new_net = api.create_network({"network": data})
            api.remove_network(new_net["network"]["id"])
            break
        except neutron_exceptions.Conflict as e:
            e_msg = f"Error occurred during creating network after {retry} retries. {e}"
        except Exception as e:
            raise ValueError(f"Error occurred during creating network. {e}") from e
    else:
        raise ValueError(e_msg)


def _validate_reserved_networks(reserved_networks: List[str]):
    for net in reserved_networks:
        # Just try to create an IPv4Network if anything, it'd raise a ValueError
        ipaddress.ip_network(net)
