import pytest

from cloudshell.cp.openstack.os_api.models import Instance


@pytest.fixture
def api_instance(os_api_v2, instance):
    return os_api_v2.Instance(instance)


def test_attach_network(simple_network, nova, api_instance: Instance):
    api_instance.attach_network(simple_network)

    nova.servers.interface_attach.assert_called_once_with(
        api_instance._os_instance, port_id=None, net_id=simple_network.id, fixed_ip=None
    )
