from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.commands import CreateInstanceCommand
from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.utils.udev import get_udev_rules


@pytest.fixture()
def command(
    rollback_manager, cancellation_context_manager, os_api_v2, deploy_app, resource_conf
):
    return CreateInstanceCommand(
        rollback_manager,
        cancellation_context_manager,
        os_api_v2,
        deploy_app,
        resource_conf,
    )


def test_create_instance(
    nova,
    resource_conf,
    deploy_app: OSNovaImgDeployApp,
    uuid_mocked,
    glance,
    neutron,
    command,
):
    availability_zone = "zone"
    affinity_group_id = "group id"
    deploy_app.availability_zone = availability_zone
    deploy_app.affinity_group_id = affinity_group_id

    flavor_id = "flavor id"
    nova.flavors.findall.return_value = [Mock(name="flavor", id=flavor_id)]
    glance.images.get.return_value = {"name": "image name", "id": deploy_app.image_id}
    neutron.show_network.return_value = {
        "network": {
            "id": resource_conf.os_mgmt_net_id,
            "name": "net name",
            "provider:network_type": "vlan",
            "provider:segmentation_id": None,
        }
    }

    command.execute()

    nova.servers.create.assert_called_once_with(
        f'{deploy_app.app_name}-{str(uuid_mocked).replace("-", "")[:8]}',
        deploy_app.image_id,
        flavor_id,
        nics=[{"net-id": resource_conf.os_mgmt_net_id}],
        userdata=get_udev_rules(),
        availability_zone=availability_zone,
        scheduler_hints={"group": affinity_group_id},
    )


def test_rollback_create_instance(
    command,
):
    instance = Mock(spec_set=Instance)
    command._instance = instance

    command.rollback()

    instance.remove.assert_called_once_with()
