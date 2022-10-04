from unittest.mock import Mock, call

import pytest

from cloudshell.cp.openstack.exceptions import PrivateIpIsNotInMgmtNetwork
from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.commands import CreateInstanceCommand
from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.utils.udev import get_udev_rules


@pytest.fixture()
def api():
    return Mock(name="OS API")


@pytest.fixture()
def image(api):
    image = Mock(name="Image")
    api.Image.get.return_value = image
    return image


@pytest.fixture()
def flavor(api):
    flavor = Mock(name="Flavor")
    api.Flavor.find_first.return_value = flavor
    return flavor


@pytest.fixture()
def mgmt_network(api):
    subnet = Mock(name="Subnet", cidr="10.0.1.0/24")
    net = Mock(name="Network", subnets=[subnet])
    api.Network.get.return_value = net
    return net


@pytest.fixture()
def iface(api):
    iface = Mock(name="iface")
    api.Instance.create.return_value = Mock(name="Instance", interfaces=[iface])
    return iface


@pytest.fixture()
def private_ip_port(api):
    port = Mock()
    api.Port.create.return_value = port
    return port


@pytest.fixture()
def command(
    rollback_manager, cancellation_context_manager, api, deploy_app, resource_conf
):
    return CreateInstanceCommand(
        rollback_manager,
        cancellation_context_manager,
        api,
        deploy_app,
        resource_conf,
    )


def test_create_instance(
    api,
    resource_conf,
    deploy_app: OSNovaImgDeployApp,
    uuid_mocked,
    command,
    cancellation_context_manager,
    image,
    flavor,
    mgmt_network,
    iface,
):
    availability_zone = "zone"
    affinity_group_id = "group id"
    extra_user_data = "user data"
    deploy_app.availability_zone = availability_zone
    deploy_app.affinity_group_id = affinity_group_id
    deploy_app.user_data = extra_user_data
    name = f'{deploy_app.app_name}-{str(uuid_mocked).replace("-", "")[:8]}'
    expected_user_data = f"{extra_user_data}\n{get_udev_rules()}"

    command.execute()

    api.assert_has_calls(
        (
            call.Image.get(deploy_app.image_id),
            call.Flavor.find_first(deploy_app.instance_flavor),
            call.Network.get(resource_conf.os_mgmt_net_id),
            call.Instance.create(
                name,
                image,
                flavor,
                network=mgmt_network,
                port=None,
                availability_zone=availability_zone,
                affinity_group_id=affinity_group_id,
                user_data=expected_user_data,
                cancellation_manager=cancellation_context_manager,
            ),
        )
    )
    assert iface.port.name == "mgmt-port"


def test_create_instance_with_private_ip(
    api,
    resource_conf,
    deploy_app: OSNovaImgDeployApp,
    uuid_mocked,
    command,
    cancellation_context_manager,
    image,
    flavor,
    mgmt_network,
    iface,
    private_ip_port,
):
    private_ip = "10.0.1.13"
    name = f'{deploy_app.app_name}-{str(uuid_mocked).replace("-", "")[:8]}'
    deploy_app.private_ip = private_ip
    deploy_app.auto_udev = False
    iface.port = private_ip_port

    command.execute()

    api.assert_has_calls(
        (
            call.Image.get(deploy_app.image_id),
            call.Flavor.find_first(deploy_app.instance_flavor),
            call.Network.get(resource_conf.os_mgmt_net_id),
            call.Port.create(
                "",
                mgmt_network,
                fixed_ip=private_ip,
                fixed_ip_subnet=mgmt_network.subnets[0],
            ),
            call.Instance.create(
                name,
                image,
                flavor,
                network=mgmt_network,
                port=private_ip_port,
                availability_zone=deploy_app.availability_zone,
                affinity_group_id=deploy_app.affinity_group_id,
                user_data="",
                cancellation_manager=cancellation_context_manager,
            ),
        )
    )
    assert iface.port.name == "mgmt-port"


def test_private_ip_is_not_inside_mgmt_network(command, mgmt_network, deploy_app):
    deploy_app.private_ip = "192.168.1.1"

    with pytest.raises(PrivateIpIsNotInMgmtNetwork):
        command._get_port_for_private_ip(mgmt_network)


def test_rollback_create_instance(
    command,
):
    instance = Mock(spec_set=Instance)
    command._instance = instance

    command.rollback()

    instance.remove.assert_called_once_with()
