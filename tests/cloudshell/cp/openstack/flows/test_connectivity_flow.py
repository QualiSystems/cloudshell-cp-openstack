from __future__ import annotations

from unittest.mock import Mock

import pytest

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ActionTargetModel,
    ConnectionModeEnum,
    ConnectivityTypeEnum,
)
from cloudshell.shell.flows.connectivity.parse_request_service import (
    ParseConnectivityRequestService,
)

from cloudshell.cp.openstack.flows import ConnectivityFlow
from cloudshell.cp.openstack.models.connectivity_models import OsConnectivityActionModel
from cloudshell.cp.openstack.os_api.models import NetworkType
from cloudshell.cp.openstack.services.network_service import QVlanNetwork


@pytest.fixture()
def connectivity_flow(resource_conf, logger, os_api_v2):
    service = ParseConnectivityRequestService(
        is_vlan_range_supported=False, is_multi_vlan_supported=False
    )
    return ConnectivityFlow(resource_conf, service, logger, os_api_v2)


@pytest.fixture()
def instance_api(os_api_v2, instance):
    return os_api_v2.Instance(instance)


@pytest.fixture()
def create_connectivity_action():
    def wrapped(
        vlan: int,
        port_mode: ConnectionModeEnum,
        qnq: bool,
        vm_uuid: str,
        connectivity_type: ConnectivityTypeEnum,
        virtual_network: str | None = None,
        subnet_cidr: str | None = None,
    ):
        return OsConnectivityActionModel(
            connectionId="id",
            connectionParams={
                "vlanId": virtual_network or str(vlan),
                "mode": port_mode,
                "type": "type",
                "vlanServiceAttributes": [
                    {"attributeName": "VLAN ID", "attributeValue": str(vlan)},
                    {"attributeName": "QnQ", "attributeValue": qnq},
                    {"attributeName": "CTag", "attributeValue": ""},
                    {
                        "attributeName": "Virtual Network",
                        "attributeValue": virtual_network,
                    },
                    {"attributeName": "Subnet CIDR", "attributeValue": subnet_cidr},
                ],
            },
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
    connectivity_flow,
    neutron_emu,
    nova,
    instance,
    create_connectivity_action,
    resource_conf,
    os_api_v2,
):
    vlan = 12
    qnq = False
    vm_uid = "vm uid"
    net_name = QVlanNetwork._get_network_name(vlan)
    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, qnq, vm_uid, ConnectivityTypeEnum.SET_VLAN
    )

    # act
    connectivity_flow._set_vlan(action)

    # validate
    created_net = os_api_v2.Network.find_by_vlan_id(vlan)
    assert created_net.name == net_name
    assert created_net.vlan_id == vlan
    assert created_net.network_type == NetworkType(resource_conf.vlan_type)

    subnet_name = QVlanNetwork._get_subnet_name(created_net.id)
    subnet = next(created_net.subnets)
    assert subnet.name == subnet_name
    assert subnet.cidr == "10.0.0.0/24"
    assert subnet.ip_version == 4
    assert subnet.gateway is None
    assert subnet.allocation_pools == []
    nova.servers.get.assert_called_once_with(vm_uid)
    nova.servers.interface_attach.assert_called_once_with(
        instance, port_id=None, net_id=created_net.id, fixed_ip=None
    )

    assert len(list(os_api_v2.Network.all())) == 1
    assert len(list(os_api_v2.Subnet.all())) == 1


def test_add_vlan_flow_failed(
    connectivity_flow, nova, neutron_emu, create_connectivity_action, os_api_v2
):
    vlan = 12
    vm_uuid = "vm uuid"
    nova.servers.interface_attach.side_effect = ValueError("failed to attach")

    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, False, vm_uuid, ConnectivityTypeEnum.SET_VLAN
    )

    with pytest.raises(ValueError, match="failed to attach"):
        connectivity_flow._set_vlan(action)

    assert len(list(os_api_v2.Network.all())) == 0
    assert len(list(os_api_v2.Subnet.all())) == 0


def test_remove_vlan_flow_not_found(
    connectivity_flow, neutron_emu, nova, create_connectivity_action
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

    # ignore removed network
    connectivity_flow._remove_vlan(action)


def test_remove_vlan_flow(
    connectivity_flow,
    neutron_emu,
    nova,
    instance,
    create_connectivity_action,
    resource_conf,
    os_api_v2,
):
    vlan = 12
    vm_uid = "vm uid"
    net_name = QVlanNetwork._get_network_name(vlan)
    net_id = "net id"
    mgmt_port_id = "mgmt port id"
    port_id = "port id"

    neutron_emu.emu_add_network(resource_conf.os_mgmt_net_id, "mgmt")
    neutron_emu.emu_add_port(mgmt_port_id, "mgmt-port", resource_conf.os_mgmt_net_id)

    neutron_emu.emu_add_network(
        net_id, net_name, NetworkType(resource_conf.vlan_type), vlan
    )
    neutron_emu.emu_add_port(port_id, "", net_id)

    instance.interface_list.return_value = [
        Mock(net_id=resource_conf.os_mgmt_net_id, port_id=mgmt_port_id),
        Mock(net_id=net_id, port_id=port_id),
    ]
    action = create_connectivity_action(
        vlan, ConnectionModeEnum.ACCESS, False, vm_uid, ConnectivityTypeEnum.REMOVE_VLAN
    )

    connectivity_flow._remove_vlan(action)

    nova.servers.get.assert_called_once_with(vm_uid)
    instance.interface_list.assert_called_once_with()
    nova.servers.interface_detach.assert_called_once_with(instance, port_id)

    assert len(list(os_api_v2.Network.all())) == 1
