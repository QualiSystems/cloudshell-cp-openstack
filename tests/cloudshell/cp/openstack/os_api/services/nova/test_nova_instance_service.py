import pytest
from novaclient import exceptions as nova_exceptions

from cloudshell.cp.openstack.exceptions import InstanceErrorStateException
from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.services import NovaService
from cloudshell.cp.openstack.os_api.services.nova.nova_instance_service import (
    NovaInstanceStatus,
    _get_udev_rules,
)


@pytest.fixture()
def nova_service(instance, nova, logger):
    return NovaService(instance, nova, logger)


@pytest.mark.parametrize(
    ("status_str", "status_enum"),
    (
        ("ACTIVE", NovaInstanceStatus.ACTIVE),
        ("active", NovaInstanceStatus.ACTIVE),
        ("error", NovaInstanceStatus.ERROR),
        ("another status", NovaInstanceStatus.OTHER),
    ),
)
def test_nova_instance_status(status_str, status_enum):
    assert NovaInstanceStatus(status_str) is status_enum
    if status_enum is NovaInstanceStatus.OTHER:
        assert NovaInstanceStatus(status_str)._real_value == status_str


def test_create_instance(
    nova,
    logger,
    resource_conf,
    deploy_app: OSNovaImgDeployApp,
    cancellation_context_manager,
    uuid_mocked,
    instance,
):
    availability_zone = "zone"
    affinity_group_id = "group id"
    instance.status = ["building", "active", "active"]
    deploy_app.availability_zone = availability_zone
    deploy_app.affinity_group_id = affinity_group_id

    NovaService.create_instance(
        nova, resource_conf, deploy_app, cancellation_context_manager, logger
    )

    nova.servers.create.assert_called_once_with(
        **{
            "name": f'{deploy_app.app_name}-{str(uuid_mocked).split("-")[0]}',
            "image": nova.glance.find_image(deploy_app.image_id),
            "flavor": nova.flavors.find(name=deploy_app.instance_flavor),
            "nics": [{"net-id": resource_conf.os_mgmt_net_id}],
            "userdata": _get_udev_rules(),
            "availability_zone": availability_zone,
            "scheduler_hints": {"group": affinity_group_id},
        }
    )


def test_create_instance_without_flavor(
    nova, resource_conf, deploy_app, cancellation_context_manager, logger
):
    deploy_app.instance_flavor = None
    with pytest.raises(ValueError, match="Instance flavor cannot be empty"):
        NovaService.create_instance(
            nova, resource_conf, deploy_app, cancellation_context_manager, logger
        )


def test_create_instance_failed(
    nova,
    logger,
    resource_conf,
    deploy_app: OSNovaImgDeployApp,
    cancellation_context_manager,
    uuid_mocked,
    instance,
):
    instance.status = ["building", "building", "error", "error"]

    with pytest.raises(InstanceErrorStateException, match="fault message"):
        NovaService.create_instance(
            nova, resource_conf, deploy_app, cancellation_context_manager, logger
        )


def test_get_with_id(nova, logger):
    instance_id = "id"

    NovaService.get_with_id(nova, instance_id, logger)

    nova.servers.find.assert_called_once_with(id=instance_id)


def test_get_with_id_not_found(nova, logger):
    instance_id = "id"
    nova.servers.find.side_effect = nova_exceptions.NotFound("404")

    with pytest.raises(nova_exceptions.NotFound):
        NovaService.get_with_id(nova, instance_id, logger)


def test_power_on(instance, nova, logger):
    instance.status = ("building", "building", "active", "active")
    ns = NovaService(instance, nova, logger)

    ns.power_on()

    instance.start.assert_called_once_with()
    instance.get.assert_called_once_with()


def test_power_off(instance, nova, logger):
    instance.status = ("active", "active", "shutoff", "shutoff")
    ns = NovaService(instance, nova, logger)

    ns.power_off()

    instance.stop.assert_called_once_with()
    instance.get.assert_called_once_with()


def test_attach_interface(nova_service):
    net_id = "net id"

    nova_service.attach_interface(net_id)

    nova_service._nova.servers.interface_attach.assert_called_once_with(
        nova_service.instance, port_id=None, net_id=net_id, fixed_ip=None
    )


def test_detach_nic_from_instance(nova_service):
    port_id = "port id"

    nova_service.detach_nic_from_instance(port_id)

    nova_service._nova.servers.interface_detach.assert_called_once_with(
        nova_service.instance, port_id
    )


def test_get_instance_image(nova_service):
    nova_service.get_instance_image()

    nova_service._nova.glance.find_image.assert_called_once_with(
        nova_service.instance.image["id"]
    )


def test_get_instance_flavor(nova_service):
    nova_service.get_instance_flavor()

    nova_service._nova.flavors.get.assert_called_once_with(
        nova_service.instance.flavor["id"]
    )


def test_terminate(nova_service):
    nova_service.terminate()

    nova_service.instance.delete.assert_called_once_with()
