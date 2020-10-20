from ipaddress import IPv4Network
from unittest.mock import Mock, call

import pytest
from neutronclient.v2_0.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.exceptions import (
    FreeSubnetIsNotFoundException,
    NetworkException,
    NetworkNotFoundException,
    SubnetNotFoundException,
)
from cloudshell.cp.openstack.os_api.services import NeutronService
from cloudshell.cp.openstack.os_api.services.neutron.neutron_network_service import (
    _generate_subnet,
)


@pytest.fixture()
def neutron_service(neutron, logger):
    return NeutronService(neutron, logger)


def test_get_network(neutron_service, neutron):
    net_id = "net id"
    neutron.list_networks.return_value = {"networks": [{"net_id": net_id}]}

    neutron_service.get_network(id=net_id)

    neutron.list_networks.assert_called_once_with(id=net_id)


@pytest.mark.parametrize(
    ("return_list", "error", "error_pattern"),
    (
        ([], NetworkNotFoundException, "Network .+ not found"),
        (
            [{"net_id": "net id"}, {"net_id": "another net id"}],
            NetworkException,
            "Found more than one network",
        ),
    ),
)
def test_get_network_failed(
    neutron_service, neutron, return_list, error, error_pattern
):
    net_id = "net id"
    neutron.list_networks.return_value = {"networks": return_list}

    with pytest.raises(error, match=error_pattern):
        neutron_service.get_network(id=net_id)


def test_get_subnet(neutron_service, neutron):
    subnet_id = "subnet id"
    neutron.list_subnets.return_value = {"subnets": [{"subnet_id": subnet_id}]}

    neutron_service.get_subnet(id=subnet_id)

    neutron.list_subnets.assert_called_once_with(id=subnet_id)


@pytest.mark.parametrize(
    ("return_list", "error", "error_pattern"),
    (
        ([], SubnetNotFoundException, "Subnet .+ not found"),
        (
            [{"subnet_id": "subnet id"}, {"subnet_id": "another subnet id"}],
            NetworkException,
            "Found more than one subnet",
        ),
    ),
)
def test_get_subnet_failed(neutron_service, neutron, return_list, error, error_pattern):
    subnet_id = "subnet id"
    neutron.list_subnets.return_value = {"subnets": return_list}

    with pytest.raises(error, match=error_pattern):
        neutron_service.get_subnet(id=subnet_id)


def test_get_network_name(neutron_service, neutron):
    net_id = "net id"
    net_name = "net name"
    neutron.list_networks.return_value = {
        "networks": [{"net_id": net_id, "name": net_name}]
    }

    assert neutron_service.get_network_name(net_id) == net_name

    neutron.list_networks.assert_called_once_with(id=net_id)


def test_create_network(neutron_service, neutron):
    new_net_dict = {"network": {"name": "net_name"}}

    neutron_service.create_network(new_net_dict)

    neutron.create_network.assert_called_once_with(new_net_dict)


def test_remove_network(neutron_service, neutron):
    net_id = "net id"
    neutron.list_ports.side_effect = (
        {"ports": [{"id": "port id 1"}, {"id": "port id 2"}]},
        {"ports": [{"id": "port id 1"}]},
    )
    neutron.list_subnets.return_value = {
        "subnets": [{"id": "subnet id 1"}, {"id": "subnet id 2"}]
    }

    neutron_service.remove_network(net_id)

    neutron.list_ports.assert_has_calls(
        [call(network_id=net_id), call(network_id=net_id)]
    )
    neutron.list_subnets.assert_called_once_with(network_id=net_id)
    neutron.delete_subnet.assert_has_calls([call("subnet id 1"), call("subnet id 2")])
    neutron.delete_network.assert_called_once_with(net_id)


def test_remove_network_more_than_one_port(neutron_service, neutron):
    net_id = "net id"
    neutron.list_ports.return_value = {
        "ports": [{"id": "port id 1"}, {"id": "port id 2"}]
    }
    neutron.list_subnets.return_value = {
        "subnets": [{"id": "subnet id 1"}, {"id": "subnet id 2"}]
    }
    neutron.delete_subnet.side_effect = neutron_exceptions.Conflict
    neutron.delete_network.side_effect = neutron_exceptions.NetworkInUseClient

    neutron_service.remove_network(net_id)

    neutron.list_ports.assert_has_calls([call(network_id=net_id)] * 4)
    neutron.list_subnets.assert_called_once_with(network_id=net_id)
    neutron.delete_subnet.assert_has_calls([call("subnet id 1"), call("subnet id 2")])
    neutron.delete_network.assert_called_once_with(net_id)


def test_remove_network_subnet_and_network_not_found(neutron_service, neutron):
    net_id = "net id"
    neutron.list_ports.return_value = {"ports": [{"id": "port id 1"}]}
    neutron.list_subnets.side_effect = SubnetNotFoundException
    neutron.delete_network.side_effect = neutron_exceptions.NetworkNotFoundClient

    neutron_service.remove_network(net_id)

    neutron.list_ports.assert_has_calls([call(network_id=net_id)])
    neutron.list_subnets.assert_called_once_with(network_id=net_id)
    neutron.delete_network.assert_called_once_with(net_id)


def test_get_or_create_net_with_segmentation_id(
    monkeypatch, neutron_service, resource_conf
):
    create_net_mock = Mock()
    get_net_mock = Mock()
    monkeypatch.setattr(
        neutron_service, "_create_net_with_segmentation_id", create_net_mock
    )
    monkeypatch.setattr(neutron_service, "get_net_with_segmentation", get_net_mock)
    segmentation_id = 101
    net_prefix = "prefix"
    create_net_mock.side_effect = neutron_exceptions.Conflict()

    net = neutron_service.get_or_create_net_with_segmentation_id(
        segmentation_id, resource_conf, net_prefix
    )

    create_net_mock.assert_called_once_with(segmentation_id, resource_conf, net_prefix)
    get_net_mock.assert_called_once_with(segmentation_id)
    assert net == get_net_mock()


def test_create_net_with_segmentation_id(neutron_service, neutron, resource_conf):
    segmentation_id = 101
    net_prefix = "net prefix"
    resource_conf.vlan_type = "vlan"

    neutron_service._create_net_with_segmentation_id(
        segmentation_id, resource_conf, net_prefix
    )

    neutron.create_network.assert_called_once_with(
        {
            "network": {
                "provider:network_type": resource_conf.vlan_type,
                "provider:segmentation_id": segmentation_id,
                "name": f"{net_prefix}_{segmentation_id}",
                "admin_state_up": True,
                "provider:physical_network": resource_conf.os_physical_int_name,
            }
        }
    )


def test_get_net_with_segmentation(neutron_service, neutron):
    segmentation_id = 101

    neutron_service.get_net_with_segmentation(segmentation_id)

    neutron.list_networks.assert_called_once_with(
        **{"provider:segmentation_id": segmentation_id}
    )


def test_get_net_with_segmentation_not_found(neutron_service, neutron):
    segmentation_id = 101
    neutron.list_networks.return_value = {"networks": []}

    emsg = f"Network with {segmentation_id} segmentation id not found"
    with pytest.raises(NetworkNotFoundException, match=emsg):
        neutron_service.get_net_with_segmentation(segmentation_id)


def test_create_subnet(neutron_service, neutron):
    net_id = "net id"
    reserved_networks = []
    neutron.list_subnets.return_value = {"subnets": []}

    neutron_service.create_subnet(net_id, reserved_networks)

    neutron.list_subnets.assert_called_once_with(fields=["cidr", "id"])
    neutron.create_subnet.assert_called_once_with(
        {
            "subnet": {
                "cidr": "10.0.0.0/24",
                "network_id": net_id,
                "ip_version": 4,
                "name": f"qs_subnet_{net_id}",
                "gateway_ip": None,
            }
        }
    )


def test_generate_subnet_not_found_free():
    blacklist_subnets = {"10.0.0.0/8"}
    blacklist_subnets.add("172.16.0.0/12")
    blacklist_subnets.add("192.168.0.0/16")
    blacklist_subnets = set(map(IPv4Network, blacklist_subnets))

    with pytest.raises(FreeSubnetIsNotFoundException, match="All Subnets Exhausted"):
        _generate_subnet(blacklist_subnets)


def test_create_floating_ip(neutron_service, neutron):
    subnet_id = "subnet id"
    port_id = "port id"
    net_id = "net id"
    neutron.list_subnets.return_value = {
        "subnets": [{"id": subnet_id, "network_id": net_id}]
    }

    ip = neutron_service.create_floating_ip(subnet_id, port_id)

    neutron.list_subnets.assert_called_once_with(id=subnet_id)
    neutron.create_floatingip.assert_called_once_with(
        {
            "floatingip": {
                "floating_network_id": net_id,
                "subnet_id": subnet_id,
                "port_id": port_id,
            }
        }
    )
    assert ip == neutron.create_floatingip()["floatingip"]["floating_ip_address"]


def test_create_floating_ip_failed(neutron_service, neutron):
    subnet_id = "subnet id"
    port_id = "port id"
    neutron.create_floatingip.return_value = {"floatingip": {}}

    with pytest.raises(NetworkException, match="Unable to assign Floating IP"):
        neutron_service.create_floating_ip(subnet_id, port_id)


def test_floating_ip(neutron_service, neutron):
    ip = "ip"
    floating_id = "floating id"
    neutron.list_floatingips.return_value = {"floatingips": [{"id": floating_id}]}

    neutron_service.delete_floating_ip(ip)

    neutron.list_floatingips.assert_called_once_with(floating_ip_address=ip)
    neutron.delete_floatingip.assert_called_once_with(floating_id)


def test_create_security_group(neutron_service, neutron):
    sg_name = "sg name"

    sg_id = neutron_service.create_security_group(sg_name)

    neutron.create_security_group.assert_called_once_with(
        {"security_group": {"name": sg_name}}
    )
    assert sg_id == neutron.create_security_group()["security_group"]["id"]


def test_create_security_group_rule(neutron_service, neutron):
    sg_id = "sg id"
    cidr = "0.0.0.0/0"
    port_min = port_max = 22
    protocol = "tcp"

    neutron_service.create_security_group_rule(
        sg_id, cidr, port_min, port_max, protocol
    )

    neutron.create_security_group_rule.assert_called_once_with(
        {
            "security_group_rule": {
                "remote_ip_prefix": cidr,
                "port_range_min": port_min,
                "port_range_max": port_max,
                "protocol": protocol,
                "security_group_id": sg_id,
                "direction": "ingress",
            }
        }
    )


def test_delete_security_group(neutron_service, neutron):
    sg_id = "sg id"

    neutron_service.delete_security_group(sg_id)

    neutron.delete_security_group.assert_called_once_with(sg_id)
