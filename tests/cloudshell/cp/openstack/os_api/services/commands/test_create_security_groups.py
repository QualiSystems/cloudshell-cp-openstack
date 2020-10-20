from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands import CreateSecurityGroup


@pytest.fixture()
def os_api():
    return Mock(name="OS API")


def test_create_security_group(
    os_api,
    deploy_app,
    rollback_manager,
    cancellation_context_manager,
    instance,
):
    command = CreateSecurityGroup(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        deploy_app,
        instance,
    )

    command.execute()

    os_api.create_security_group_for_instance.assert_called_once_with(
        instance, deploy_app.inbound_ports
    )
    assert command._sg_id == os_api.create_security_group_for_instance()


def test_rollback_create_security_groups(
    os_api,
    deploy_app,
    rollback_manager,
    cancellation_context_manager,
    instance,
):
    command = CreateSecurityGroup(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        deploy_app,
        instance,
    )

    command.rollback()

    os_api.delete_security_group_for_instance.assert_called_once_with(command._instance)
