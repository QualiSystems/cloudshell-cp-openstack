from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands import CreateFloatingIP


@pytest.fixture()
def os_api():
    return Mock(name="OS API")


def test_create_floating_ip(
    os_api,
    resource_conf,
    deploy_app,
    instance,
    rollback_manager,
    cancellation_context_manager,
):
    port_id = "port id"
    instance.interface_list.return_value = [Mock(port_id=port_id)]
    command = CreateFloatingIP(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        resource_conf,
        deploy_app,
        instance,
    )

    ip = command.execute()

    os_api.create_floating_ip.assert_called_once_with(
        deploy_app.floating_ip_subnet_id, port_id
    )
    assert ip == os_api.create_floating_ip()


def test_create_floating_ip_from_r_conf(
    os_api,
    resource_conf,
    deploy_app,
    instance,
    rollback_manager,
    cancellation_context_manager,
):
    deploy_app.floating_ip_subnet_id = ""
    port_id = "port id"
    instance.interface_list.return_value = [Mock(port_id=port_id)]
    command = CreateFloatingIP(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        resource_conf,
        deploy_app,
        instance,
    )

    ip = command.execute()

    os_api.create_floating_ip.assert_called_once_with(
        resource_conf.floating_ip_subnet_id, port_id
    )
    assert ip == os_api.create_floating_ip()


def test_rollback_create_floating_ip(
    os_api,
    resource_conf,
    deploy_app,
    instance,
    rollback_manager,
    cancellation_context_manager,
):
    command = CreateFloatingIP(
        rollback_manager,
        cancellation_context_manager,
        os_api,
        resource_conf,
        deploy_app,
        instance,
    )

    command.rollback()

    os_api.delete_floating_ip.assert_called_once_with(command._ip)
