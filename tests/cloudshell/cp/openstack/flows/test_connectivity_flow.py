from unittest.mock import Mock

import pytest

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ActionTargetModel,
    ConnectionModeEnum,
    ConnectionParamsModel,
    ConnectivityActionModel,
    ConnectivityTypeEnum,
)
from cloudshell.shell.flows.connectivity.parse_request_service import (
    ParseConnectivityRequestService,
)

from cloudshell.cp.openstack.exceptions import NetworkNotFound
from cloudshell.cp.openstack.flows import ConnectivityFlow
from cloudshell.cp.openstack.services.network_service import QVlanNetwork


@pytest.fixture()
def connectivity_flow(resource_conf, logger, os_api_v2):
    service = ParseConnectivityRequestService(
        is_vlan_range_supported=False, is_multi_vlan_supported=False
    )
    return ConnectivityFlow(resource_conf, service, logger, os_api_v2)


@pytest.fixture()
def create_connectivity_action():
    def wrapped(
        vlan: int,
        port_mode: ConnectionModeEnum,
        qnq: bool,
        vm_uuid: str,
        connectivity_type: ConnectivityTypeEnum,
    ):
        return ConnectivityActionModel(
            connectionId="id",
            connectionParams=ConnectionParamsModel(
                vlanId=str(vlan),
                mode=port_mode,
                type="type",
                vlanServiceAttributes=[
                    {"attributeName": "QnQ", "attributeValue": qnq},
                    {"attributeName": "CTag", "attributeValue": ""},
                ],
            ),
            connectorAttributes=[{"attributeName": "Interface", "attributeValue": ""}],
            actionTarget=ActionTargetModel(fullName="", fullAddress="full address"),
            customActionAttributes=[
                {"attributeName": "VM_UUID", "attributeValue": vm_uuid}
            ],
            actionId="action_id",
            type=connectivity_type,
        )

    return wrapped


def test_add_vlan_flow(
    connectivity_flow, neutron, nova, instance, create_connectivity_action
):
    vlan = 12
    qnq = False
    vm_uid = "vm uid"
    net_id = "net id"
    net_name = QVlanNetwork._get_network_name(vlan)
    subnet_name = QVlanNetwork._get_subnet_name(net_id)
    neutron.create_network.return_value = {
        "network": {
            "id": net_id,
            "subnets": [],
            "name": net_name,
            "provider:network_type": connectivity_flow._resource_conf.vlan_type.lower(),
            "provider:segmentation_id": vlan,
        }
    }
    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, qnq, vm_uid, ConnectivityTypeEnum.SET_VLAN
    )

    # act
    connectivity_flow._set_vlan(action)

    # validate
    neutron.create_network.assert_called_once_with(
        {
            "network": {
                "provider:network_type": (
                    connectivity_flow._resource_conf.vlan_type.lower()
                ),
                "provider:segmentation_id": vlan,
                "name": net_name,
                "admin_state_up": True,
            }
        }
    )
    neutron.create_subnet.assert_called_once_with(
        {
            "subnet": {
                "name": subnet_name,
                "network_id": net_id,
                "cidr": "10.0.0.0/24",
                "ip_version": 4,
                "gateway_ip": None,
            }
        }
    )
    nova.servers.get.assert_called_once_with(vm_uid)
    nova.servers.interface_attach.assert_called_once_with(
        instance, port_id=None, net_id=net_id, fixed_ip=None
    )


def test_add_vlan_flow_failed(
    connectivity_flow, nova, neutron, create_connectivity_action
):
    vlan = 12
    net_id = "net id"
    vm_uuid = "vm uuid"
    net_name = QVlanNetwork._get_network_name(vlan)
    neutron.create_network.return_value = {
        "network": {
            "id": net_id,
            "subnets": [],
            "name": net_name,
            "provider:network_type": connectivity_flow._resource_conf.vlan_type.lower(),
            "provider:segmentation_id": vlan,
        }
    }
    nova.servers.interface_attach.side_effect = ValueError("failed to attach")
    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, False, vm_uuid, ConnectivityTypeEnum.SET_VLAN
    )

    with pytest.raises(ValueError, match="failed to attach"):
        connectivity_flow._set_vlan(action)

    neutron.delete_network.assert_called_once_with(net_id)


def test_remove_vlan_flow_not_found(
    connectivity_flow, neutron, nova, create_connectivity_action
):
    vlan = 13
    vm_uuid = "vm uuid"
    action = create_connectivity_action(
        vlan,
        ConnectionModeEnum.ACCESS,
        False,
        vm_uuid,
        ConnectivityTypeEnum.REMOVE_VLAN,
    )
    neutron.list_networks.side_effect = NetworkNotFound(vlan_id=vlan)

    connectivity_flow._remove_vlan(action)

    neutron.delete_network.assert_not_called()


def test_remove_vlan_flow(
    connectivity_flow, neutron, nova, instance, create_connectivity_action
):
    vlan = 12
    vm_uid = "vm uid"
    net_name = "net name"
    net_id = "net id"
    port_id = "port id"
    net_dict = {
        "name": net_name,
        "id": net_id,
        "provider:network_type": connectivity_flow._resource_conf.vlan_type.lower(),
        "provider:segmentation_id": vlan,
    }
    neutron.list_networks.return_value = {"networks": [net_dict]}
    instance.interface_list.return_value = [Mock(net_id=net_id, port_id=port_id)]
    neutron.show_port.return_value = {
        "port": {
            "id": port_id,
            "name": "port name",
            "network_id": net_id,
            "mac_address": "mac address",
        }
    }
    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, False, vm_uid, ConnectivityTypeEnum.REMOVE_VLAN
    )

    connectivity_flow._remove_vlan(action)

    nova.servers.get.assert_called_once_with(vm_uid)
    instance.interface_list.assert_called_once_with()
    neutron.list_networks.assert_called_once_with(**{"provider:segmentation_id": vlan})
    nova.servers.interface_detach.assert_called_once_with(instance, port_id)
    neutron.delete_network.assert_called_once_with(net_id)
