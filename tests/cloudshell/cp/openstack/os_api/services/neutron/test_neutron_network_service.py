from unittest.mock import call

import pytest
from neutronclient.v2_0.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.exceptions import (
    NetworkException,
    NetworkNotFoundException,
    SubnetNotFoundException,
)
from cloudshell.cp.openstack.os_api.services import NeutronService


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


def test_remove_network(neutron_service, neutron, sleepless):
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


def test_remove_network_more_than_one_port(neutron_service, neutron, sleepless):
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


def test_remove_network_subnet_and_network_not_found(
    neutron_service, neutron, sleepless
):
    net_id = "net id"
    neutron.list_ports.return_value = {"ports": [{"id": "port id 1"}]}
    neutron.list_subnets.side_effect = SubnetNotFoundException
    neutron.delete_network.side_effect = neutron_exceptions.NetworkNotFoundClient

    neutron_service.remove_network(net_id)

    neutron.list_ports.assert_has_calls([call(network_id=net_id)])
    neutron.list_subnets.assert_called_once_with(network_id=net_id)
    neutron.delete_network.assert_called_once_with(net_id)
