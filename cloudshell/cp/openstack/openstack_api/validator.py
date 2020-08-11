import ipaddress
import random
from typing import List

import keystoneauth1.exceptions
from keystoneauth1.session import Session
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client

from cloudshell.cp.openstack.resource_config import OSResourceConfig


def validate_os_session(os_session: Session, resource_conf: OSResourceConfig):
    _validate_resource_conf(resource_conf)
    _validate_connection(os_session, resource_conf)
    _validate_network_attributes(os_session, resource_conf)


def _validate_resource_conf(resource_conf: OSResourceConfig):
    _is_not_empty(resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url)
    _is_http_url(resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url)

    _is_not_empty(resource_conf.os_domain_name, resource_conf.ATTR_NAMES.os_domain_name)
    _is_not_empty(
        resource_conf.os_project_name, resource_conf.ATTR_NAMES.os_project_name
    )
    _is_not_empty(resource_conf.username, resource_conf.ATTR_NAMES.username)
    _is_not_empty(resource_conf.password, resource_conf.ATTR_NAMES.password)
    _is_not_empty(resource_conf.os_mgmt_net_id, resource_conf.ATTR_NAMES.os_mgmt_net_id)
    _is_not_empty(
        resource_conf.floating_ip_subnet_id,
        resource_conf.ATTR_NAMES.floating_ip_subnet_id,
    )
    if resource_conf.vlan_type.lower() not in ("vlan", "vxlan"):
        raise ValueError('Vlan Type should be one of "VLAN" or "VXLAN".')


def _is_not_empty(value: str, err_value: str):
    if not value:
        raise ValueError(f"{err_value} cannot be empty")


def _is_http_url(value: str, err_value: str):
    v = value.lower()
    if not v.startswith("http://") or v.startswith("https://"):
        raise ValueError(f"{value} is not valid format for {err_value}")


def _validate_connection(os_session: Session, resource_conf: OSResourceConfig):
    client_version = "2.0"
    try:
        client = nova_client.Client(client_version, session=os_session)
        client.servers.list()
    except (
        keystoneauth1.exceptions.http.BadRequest,
        keystoneauth1.exceptions.http.Unauthorized,
    ):
        raise
    except keystoneauth1.exceptions.http.NotFound:
        raise ValueError(f"Controller URL {resource_conf.controller_url} is not found")
    except Exception as e:
        raise ValueError(f"One or more values are not correct. {e}")


def _validate_network_attributes(os_session: Session, resource_conf: OSResourceConfig):
    client = neutron_client.Client(session=os_session, insecure=True)
    _get_network_id(client, resource_conf.os_mgmt_net_id)
    _validate_floating_ip_subnet(client, resource_conf.floating_ip_subnet_id)
    _validate_vlan_type(
        client, resource_conf.vlan_type, resource_conf.os_physical_int_name
    )
    _validate_reserved_networks(resource_conf.os_reserved_networks)


def _get_network_id(neut_client: neutron_client.Client, network_id: str):
    try:
        net_lst = neut_client.list_networks(id=network_id)["networks"]
    except Exception as e:
        raise ValueError(f"Error getting network. {e}")
    else:
        if not net_lst:
            raise ValueError(f"Network with ID {network_id} Not Found")
        elif len(net_lst) > 1:
            raise ValueError(f"More than one network matching ID {network_id} Found")
        return net_lst[0]


def _validate_floating_ip_subnet(
    neut_client: neutron_client.Client, floating_ip_subnet_id: str
):
    subnet = neut_client.show_subnet(floating_ip_subnet_id)
    ext_net_id = subnet["subnet"]["network_id"]
    ext_net = _get_network_id(neut_client, ext_net_id)
    if not ext_net["router:external"]:
        msg = f"Network with ID {ext_net_id} exists but is not an external network"
        raise ValueError(msg)


def _validate_vlan_type(
    neut_client: neutron_client.Client, vlan_type: str, os_physical_int: str
):
    e_msg = ""
    for retry in range(10):
        data = {
            "provider:network_type": vlan_type.lower(),
            "name": "qs_autoload_validation_net",
            "provider:segmentation_id": random.randint(100, 4000),
            "admin_state_up": True,
        }
        if vlan_type.lower() == "vlan":
            data["provider:physical_network"] = os_physical_int
        try:
            new_net = neut_client.create_network({"network": data})
            neut_client.delete_network(new_net["network"]["id"])
            break
        except neutron_client.exceptions.Conflict as e:
            e_msg = f"Error occurred during creating network after {retry} retries. {e}"
        except Exception as e:
            raise ValueError(f"Error occurred during creating network. {e}")
    else:
        raise ValueError(e_msg)


def _validate_reserved_networks(reserved_networks: List[str]):
    for net in reserved_networks:
        # Just try to create an IPv4Network if anything, it'd raise a ValueError
        ipaddress.ip_network(net)
