from unittest.mock import Mock, call

import pytest

from cloudshell.cp.openstack.exceptions import NetworkNotFoundException
from cloudshell.cp.openstack.flows import ConnectivityFlow


@pytest.fixture()
def connectivity_flow(resource_conf, os_api, logger):
    return ConnectivityFlow(resource_conf, os_api, logger)


def test_add_vlan_flow(connectivity_flow, neutron, nova, instance):
    vlan = 12
    port_mode = ""
    full_name = ""
    qnq = False
    c_tag = ""
    vm_uid = "vm uid"
    net_id = "net id"
    neutron.create_network.return_value = {"network": {"id": net_id, "subnets": []}}

    connectivity_flow._add_vlan_flow(
        str(vlan), port_mode, full_name, qnq, c_tag, vm_uid
    )

    neutron.create_network.assert_called_once_with(
        {
            "network": {
                "provider:network_type": (
                    connectivity_flow._resource_conf.vlan_type.lower()
                ),
                "provider:segmentation_id": vlan,
                "name": f"{connectivity_flow._api.NET_WITH_SEGMENTATION_PREFIX}_{vlan}",
                "admin_state_up": True,
            }
        }
    )
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
    nova.servers.find.assert_called_once_with(id=vm_uid)
    nova.servers.interface_attach.assert_called_once_with(
        instance, port_id=None, net_id=net_id, fixed_ip=None
    )


def test_add_vlan_flow_failed(connectivity_flow, nova, neutron):
    net_id = "net id"
    neutron.create_network.return_value = {"network": {"id": net_id, "subnets": []}}
    nova.servers.interface_attach.side_effect = ValueError("failed to attach")

    with pytest.raises(ValueError, match="failed to attach"):
        connectivity_flow._add_vlan_flow("12", "", "", False, "", "vm uid")

    neutron.delete_network.assert_called_once_with(net_id)


def test_remove_vlan_flow_not_found(connectivity_flow, neutron, nova):
    neutron.list_networks.side_effect = NetworkNotFoundException("not found")

    connectivity_flow._remove_vlan_flow("12", "", "", "")

    nova.servers.find.assert_not_called()


def test_remove_vlan_flow(connectivity_flow, neutron, nova, instance):
    vlan = 12
    vm_uid = "vm uid"
    net_name = "net name"
    net_id = "net id"
    port_id = "port id"
    neutron.list_networks.return_value = {
        "networks": [{"name": net_name, "id": net_id}]
    }
    instance.interface_list.return_value = [Mock(net_id=net_id, port_id=port_id)]

    connectivity_flow._remove_vlan_flow(str(vlan), "", "", vm_uid)

    nova.servers.find.assert_called_once_with(id=vm_uid)
    instance.interface_list.assert_called_once_with()
    neutron.list_networks.assert_has_calls(
        [call(**{"provider:segmentation_id": vlan}), call(id=net_id)]
    )
    nova.servers.interface_detach.assert_called_once_with(instance, port_id)
    neutron.delete_network.assert_called_once_with(net_id)


def test_remove_all_vlan_flow(connectivity_flow, nova, neutron, instance):
    vm_uid = "vm uid"
    net_name = f"{connectivity_flow._api.NET_WITH_SEGMENTATION_PREFIX}net name"
    net_id = "net id"
    instance.networks = {net_name: []}
    neutron.list_networks.return_value = {
        "networks": [{"name": net_name, "id": net_id}]
    }

    connectivity_flow._remove_all_vlan_flow("", vm_uid)

    nova.servers.find.assert_called_once_with(id=vm_uid)
    neutron.list_networks.assert_called_once_with(name=net_name)
    nova.servers.interface_detach.assert_called_once_with(instance, net_id)
    neutron.delete_network.assert_called_once_with(net_id)
