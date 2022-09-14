import pytest

from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.os_api.models.instance import InstanceStatus


@pytest.fixture
def api_instance(os_api_v2, instance):
    return os_api_v2.Instance(instance)


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
