from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands import CreateInstanceCommand


@pytest.fixture()
def os_api():
    return Mock(name="OS API")


def test_create_instance(
    os_api,
    deploy_app,
    rollback_manager,
    cancellation_context_manager,
):
    command = CreateInstanceCommand(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        deploy_app,
    )

    instance = command.execute()

    os_api.create_instance.assert_called_once_with(
        deploy_app, cancellation_context_manager
    )
    assert instance == os_api.create_instance()


def test_rollback_create_instance(
    os_api,
    deploy_app,
    rollback_manager,
    cancellation_context_manager,
):
    command = CreateInstanceCommand(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        deploy_app,
    )

    command.rollback()

    os_api.terminate_instance.assert_called_once_with(command._instance)
