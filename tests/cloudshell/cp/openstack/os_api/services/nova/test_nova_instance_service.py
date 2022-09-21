import pytest
from novaclient import exceptions as nova_exceptions

from cloudshell.cp.openstack.os_api.services import NovaService
from cloudshell.cp.openstack.os_api.services.nova.nova_instance_service import (
    NovaInstanceStatus,
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


def test_get_with_id(nova, logger):
    instance_id = "id"

    NovaService.get_with_id(nova, instance_id, logger)

    nova.servers.find.assert_called_once_with(id=instance_id)


def test_get_with_id_not_found(nova, logger):
    instance_id = "id"
    nova.servers.find.side_effect = nova_exceptions.NotFound("404")

    with pytest.raises(nova_exceptions.NotFound):
        NovaService.get_with_id(nova, instance_id, logger)


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
