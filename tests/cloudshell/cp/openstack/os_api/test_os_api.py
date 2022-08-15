from unittest.mock import Mock, call

import pytest

from cloudshell.cp.openstack.models.deploy_app import SecurityGroupRule
from cloudshell.cp.openstack.os_api.services.nova.nova_instance_service import (
    _get_udev_rules,
)


def test_create_instance(
    os_api,
    deploy_app,
    cancellation_context_manager,
    nova,
    uuid_mocked,
    resource_conf,
):
    os_api.create_instance(deploy_app, cancellation_context_manager)

    nova.servers.create.assert_called_once_with(
        **{
            "name": f'{deploy_app.app_name}-{str(uuid_mocked).split("-")[0]}',
            "image": nova.glance.find_image(deploy_app.image_id),
            "flavor": nova.flavors.find(name=deploy_app.instance_flavor),
            "nics": [{"net-id": resource_conf.os_mgmt_net_id}],
            "userdata": _get_udev_rules(),
        }
    )


def test_get_network_dict(os_api, neutron):
    net_id = "net id"

    dict_ = os_api.get_network_dict(id=net_id)

    neutron.list_networks.assert_called_once_with(id=net_id)
    assert dict_ == neutron.list_networks()["networks"][0]


def test_get_network_name(os_api, neutron):
    net_id = "net id"

    name = os_api.get_network_name(net_id)

    neutron.list_networks.assert_called_once_with(id=net_id)
    assert name == neutron.list_networks()["networks"][0]["name"]


def test_get_network_id_for_subnet_id(os_api, neutron):
    subnet_id = "subnet id"

    net_id = os_api.get_network_id_for_subnet_id(subnet_id)

    neutron.list_subnets.assert_called_once_with(id=subnet_id)
    assert net_id == neutron.list_subnets()["subnets"][0]["network_id"]


def test_create_floating_ip(os_api, neutron):
    subnet_id = "subnet id"
    port_id = "port id"

    ip = os_api.create_floating_ip(subnet_id, port_id)

    neutron.list_subnets.assert_called_once_with(id=subnet_id)
    neutron.create_floatingip.assert_called_once_with(
        {
            "floatingip": {
                "floating_network_id": neutron.list_subnets()["subnets"][0][
                    "network_id"
                ],
                "subnet_id": subnet_id,
                "port_id": port_id,
            }
        }
    )
    assert ip == neutron.create_floatingip()["floatingip"]["floating_ip_address"]


def test_delete_floating_ip(os_api, neutron):
    ip = "floating ip"

    os_api.delete_floating_ip(ip)

    neutron.list_floatingips.assert_called_once_with(floating_ip_address=ip)
    neutron.delete_floatingip.assert_called_once_with(
        neutron.list_floatingips()["floatingips"][0]["id"]
    )


def test_get_image_from_instance(os_api, instance, nova):
    img = os_api.get_image_from_instance(instance)

    nova.glance.find_image.assert_called_once_with(instance.image["id"])
    assert img == nova.glance.find_image()


def test_get_flavor_from_instance(os_api, instance, nova):
    flavor = os_api.get_flavor_from_instance(instance)

    nova.flavors.get.assert_called_once_with(instance.flavor["id"])
    assert flavor == nova.flavors.get()


def test_terminate_instance(os_api, instance):
    os_api.terminate_instance(instance)

    instance.delete.assert_called_once_with()


def test_get_instance(os_api, nova):
    instance_id = "inst id"

    inst = os_api.get_instance(instance_id)

    nova.servers.find.assert_called_once_with(id=instance_id)
    assert inst == nova.servers.find()


def test_power_on_instance(os_api, instance):
    instance.status = ["building", "building", "active", "active"]

    os_api.power_on_instance(instance)

    instance.start.assert_called_once_with()
    instance.get.assert_called_once_with()


def test_power_off_instance(os_api, instance):
    instance.status = ["active", "active", "shutoff", "shutoff"]

    os_api.power_off_instance(instance)

    instance.stop.assert_called_once_with()
    instance.get.assert_called_once_with()


def test_create_network(os_api, neutron):
    net_data = {"name": "net name"}

    os_api.create_network(net_data)

    neutron.create_network.assert_called_once_with(net_data)


def test_remove_network(os_api, neutron):
    net_id = "net id"
    neutron.list_ports.return_value = {"ports": []}
    neutron.list_subnets.return_value = {"subnets": [{"id": "id1"}, {"id": "id2"}]}

    os_api.remove_network(net_id)

    neutron.list_ports.assert_called_once_with(network_id=net_id)
    neutron.list_subnets(network_id=net_id)
    neutron.delete_subnet.assert_has_calls([call("id1"), call("id2")])
    neutron.delete_network.assert_called_once_with(net_id)


def test_create_security_group_for_instance(os_api, instance, neutron):
    rules = [SecurityGroupRule.from_str("22-24")]

    sg_id2 = os_api.create_security_group_for_instance(instance, rules)

    neutron.create_security_group.assert_called_once_with(
        {"security_group": {"name": f"sg-{instance.name}"}}
    )
    sg_id = neutron.create_security_group()["security_group"]["id"]
    neutron.create_security_group_rule.assert_called_once_with(
        {
            "security_group_rule": {
                "remote_ip_prefix": "0.0.0.0/0",
                "port_range_min": 22,
                "port_range_max": 24,
                "protocol": "tcp",
                "security_group_id": sg_id,
                "direction": "ingress",
            }
        }
    )
    instance.add_security_group.assert_called_once_with(sg_id)
    assert sg_id == sg_id2


def test_create_security_group_for_instance_failed(os_api, instance, neutron):
    rules = [SecurityGroupRule.from_str("22")]
    neutron.create_security_group_rule.side_effect = ValueError(
        "failed to create SG rule"
    )

    with pytest.raises(ValueError, match="failed to create SG rule"):
        os_api.create_security_group_for_instance(instance, rules)


def test_delete_security_group_for_instance(os_api, instance, neutron):
    sg_id = "sg id"
    sg = Mock(id=sg_id)
    sg.name = f"sg-{instance.name}"
    instance.list_security_group.return_value = [sg]

    os_api.delete_security_group_for_instance(instance)

    instance.list_security_group.assert_called_once_with()
    instance.remove_security_group.assert_called_once_with(sg_id)
    neutron.delete_security_group.assert_called_once_with(sg_id)
