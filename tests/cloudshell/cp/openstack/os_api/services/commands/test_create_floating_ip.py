from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands import CreateFloatingIP
from cloudshell.cp.openstack.os_api.models import FloatingIp


@pytest.fixture()
def api():
    return Mock(name="OS API")


@pytest.fixture()
def iface():
    return Mock(name="iface")


@pytest.fixture()
def command(
    rollback_manager,
    cancellation_context_manager,
    api,
    deploy_app,
    resource_conf,
    iface,
):
    return CreateFloatingIP(
        rollback_manager,
        cancellation_context_manager,
        api,
        resource_conf,
        deploy_app,
        iface,
    )


def test_create_floating_ip(command, api, iface, deploy_app):
    command.execute()

    api.Subnet.get.assert_called_once_with(deploy_app.floating_ip_subnet_id)
    api.FloatingIp.create.assert_called_once_with(api.Subnet.get(), iface.port)


def test_create_called_with_floating_subnet_from_config(
    command, api, iface, deploy_app, resource_conf
):
    deploy_app.floating_ip_subnet_id = None

    command.execute()

    api.Subnet.get.assert_called_once_with(resource_conf.floating_ip_subnet_id)
    api.FloatingIp.create.assert_called_once_with(
        api.Subnet.get(resource_conf.floating_ip_subnet_id),
        iface.port,
    )


def test_rollback(command, os_api_v2):
    floating_ip = Mock(spec_set=FloatingIp)
    command._ip = floating_ip

    command.rollback()

    floating_ip.remove.assert_called_once_with()
