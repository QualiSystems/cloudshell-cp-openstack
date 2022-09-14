from ipaddress import IPv4Address, IPv4Network

import pytest

from cloudshell.cp.openstack.exceptions import SubnetCidrFormatError
from cloudshell.cp.openstack.models.connectivity_models import (
    OsConnectivityActionModel,
    SubnetCidrData,
)


def test_connectivity_model():
    virtual_network = "Vlan170"
    subnet_cidr = "192.168.10.0/24;192.168.10.1;192.168.10.13-192.168.10.113"
    expected_subnet_cidr_data = SubnetCidrData(
        cidr=IPv4Network("192.168.10.0/24"),
        gateway=IPv4Address("192.168.10.1"),
        allocation_pool=(IPv4Address("192.168.10.13"), IPv4Address("192.168.10.113")),
    )
    vlan_id = "13"
    connectivity_action_data = {
        "connectionId": "ff051d7b-8a64-475a-87c5-4ec92b05fcf8",
        "connectionParams": {
            "vlanId": virtual_network,
            "mode": "Access",
            "vlanServiceAttributes": [
                {
                    "attributeName": "QnQ",
                    "attributeValue": "False",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "CTag",
                    "attributeValue": "",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Isolation Level",
                    "attributeValue": "Shared",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Access Mode",
                    "attributeValue": "Access",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "VLAN ID",
                    "attributeValue": vlan_id,
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Pool Name",
                    "attributeValue": "",
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Virtual Network",
                    "attributeValue": virtual_network,
                    "type": "vlanServiceAttribute",
                },
                {
                    "attributeName": "Subnet CIDR",
                    "attributeValue": subnet_cidr,
                    "type": "vlanServiceAttribute",
                },
            ],
            "type": "setVlanParameter",
        },
        "connectorAttributes": [],
        "actionTarget": {
            "fullName": "cirros-9ba5add8",
            "fullAddress": "192.168.42.240",
            "type": "actionTarget",
        },
        "customActionAttributes": [
            {
                "attributeName": "VM_UUID",
                "attributeValue": "4261f6ce-bf74-46af-8fa5-e180d6f3fbd8",
                "type": "customAttribute",
            }
        ],
        "actionId": "ff051d7b-8a64-475a-87c5-4ec92b05fcf8_ac4e3fa1-a192"
        "-4e06-8f5d-90a082c28f17",
        "type": "setVlan",
    }

    action = OsConnectivityActionModel(**connectivity_action_data)

    assert action.connection_params.vlan_service_attrs.vlan_id == vlan_id
    assert action.connection_params.vlan_id != vlan_id  # not expected
    assert action.connection_params.vlan_id == virtual_network  # not expected

    assert (
        action.connection_params.vlan_service_attrs.virtual_network == virtual_network
    )
    assert (
        action.connection_params.vlan_service_attrs.subnet_cidr
        == expected_subnet_cidr_data
    )


@pytest.mark.parametrize(
    ("subnet_cidr", "cidr", "gateway", "allocation_pool"),
    (
        (
            "192.168.10.0/24;192.168.10.1;192.168.10.100-192.168.10.200",
            IPv4Network("192.168.10.0/24"),
            IPv4Address("192.168.10.1"),
            (IPv4Address("192.168.10.100"), IPv4Address("192.168.10.200")),
        ),
        (
            "192.168.10.0/24",
            IPv4Network("192.168.10.0/24"),
            None,
            None,
        ),
        (
            "192.168.10.0/24;192.168.10.1",
            IPv4Network("192.168.10.0/24"),
            IPv4Address("192.168.10.1"),
            None,
        ),
        (
            "192.168.10.0/24;192.168.10.100-192.168.10.200",
            IPv4Network("192.168.10.0/24"),
            None,
            (IPv4Address("192.168.10.100"), IPv4Address("192.168.10.200")),
        ),
    ),
)
def test_subnet_cidr_data(subnet_cidr, cidr, gateway, allocation_pool):
    cidr_data = SubnetCidrData.from_str(subnet_cidr)

    assert cidr_data.cidr == cidr
    assert cidr_data.gateway == gateway
    assert cidr_data.allocation_pool == allocation_pool


def test_subnet_cidr_wrong_format():
    with pytest.raises(SubnetCidrFormatError):
        SubnetCidrData.from_str("192.168.13.1")


def test_subnet_gateway_wrong():
    with pytest.raises(SubnetCidrFormatError):
        SubnetCidrData.from_str("192.168.13.0/24;192.168.1")
