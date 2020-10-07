import pytest

from cloudshell.cp.openstack.exceptions import InstanceErrorStateException
from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.services import NovaService
from cloudshell.cp.openstack.os_api.services.nova.nova_instance_service import (
    NovaInstanceStatus,
    _get_udev_rules,
)


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
    sleepless,
    nova_instance_factory,
):
    availability_zone = "zone"
    affinity_group_id = "group id"
    nova.servers.create.return_value = nova_instance_factory(
        ["building", "active", "active"]
    )
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
    sleepless,
    nova_instance_factory,
):
    nova.servers.create.return_value = nova_instance_factory(
        ["building", "building", "error", "error"]
    )

    with pytest.raises(InstanceErrorStateException, match="fault message"):
        NovaService.create_instance(
            nova, resource_conf, deploy_app, cancellation_context_manager, logger
        )
