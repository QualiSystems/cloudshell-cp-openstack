from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.exceptions import InstanceErrorState
from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.os_api.models.instance import InstanceStatus


@pytest.mark.parametrize(
    ("status_str", "status_enum"),
    (
        ("ACTIVE", InstanceStatus.ACTIVE),
        ("active", InstanceStatus.ACTIVE),
        ("error", InstanceStatus.ERROR),
        ("another status", InstanceStatus.OTHER),
    ),
)
def test_instance_status(status_str, status_enum):
    assert InstanceStatus(status_str) is status_enum
    if status_enum is InstanceStatus.OTHER:
        assert InstanceStatus(status_str)._real_value == status_str


@pytest.fixture
def api_instance(os_api_v2, instance):
    return os_api_v2.Instance(instance)


def test_create(os_api_v2, nova, glance):
    name = "instance name"
    image = Mock(name="image")
    flavor = Mock(name="flavor")
    network = Mock(name="network")

    instance = os_api_v2.Instance.create(name, image, flavor, network)

    nova.servers.create.assert_called_once_with(
        name,
        image.id,
        flavor.id,
        nics=[{"net-id": network.id}],
        userdata=None,
        availability_zone=None,
        scheduler_hints=None,
    )
    instance._os_instance.delete.assert_not_called()


def test_instance_started_with_error(os_api_v2, nova, nova_instance_factory):
    name = "instance name"
    image = Mock(name="image")
    flavor = Mock(name="flavor")
    network = Mock(name="network")
    os_instance = nova_instance_factory("error")
    nova.servers.create.return_value = os_instance

    with pytest.raises(InstanceErrorState):
        os_api_v2.Instance.create(name, image, flavor, network)

    os_instance.delete.assert_called_once_with()


def test_attach_network(simple_network, nova, api_instance: Instance):
    api_instance.attach_network(simple_network)

    nova.servers.interface_attach.assert_called_once_with(
        api_instance._os_instance, port_id=None, net_id=simple_network.id, fixed_ip=None
    )


def test_power_on(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(InstanceStatus.SHUTOFF.value)
    instance = os_api_v2.Instance(os_instance)

    instance.power_on()

    os_instance.start.assert_called_once()
    os_instance.stop.assert_not_called()


def test_power_on_active(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(InstanceStatus.ACTIVE.value)
    instance = os_api_v2.Instance(os_instance)

    instance.power_on()

    os_instance.start.assert_not_called()
    os_instance.stop.assert_not_called()


def test_power_on_wait(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(
        (
            InstanceStatus.SHUTOFF.value,
            InstanceStatus.SHUTOFF.value,
            InstanceStatus.SHUTOFF.value,
            InstanceStatus.BUILDING.value,
            InstanceStatus.BUILDING.value,
            InstanceStatus.BUILDING.value,
            InstanceStatus.BUILDING.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
        )
    )
    instance = os_api_v2.Instance(os_instance)

    instance.power_on()

    os_instance.start.assert_called_once()
    os_instance.stop.assert_not_called()


def test_power_off(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(InstanceStatus.ACTIVE.value)
    instance = os_api_v2.Instance(os_instance)

    instance.power_off()

    os_instance.stop.assert_called_once()
    os_instance.start.assert_not_called()


def test_power_off_shutoff(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(InstanceStatus.SHUTOFF.value)
    instance = os_api_v2.Instance(os_instance)

    instance.power_off()

    os_instance.stop.assert_not_called()
    os_instance.start.assert_not_called()


def test_power_off_wait(nova_instance_factory, os_api_v2):
    os_instance = nova_instance_factory(
        (
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.ACTIVE.value,
            InstanceStatus.SHUTOFF.value,
            InstanceStatus.SHUTOFF.value,
            InstanceStatus.SHUTOFF.value,
        )
    )
    instance = os_api_v2.Instance(os_instance)

    instance.power_off()

    os_instance.stop.assert_called_once()
    os_instance.start.assert_not_called()
