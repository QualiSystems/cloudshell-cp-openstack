from unittest.mock import Mock, PropertyMock

import pytest

from cloudshell.cp.openstack.flows import DeployAppFromNovaImgFlow


@pytest.fixture()
def api():
    return Mock(name="OS API")


@pytest.fixture()
def deploy_app_flow(resource_conf, cancellation_context_manager, api, logger):
    return DeployAppFromNovaImgFlow(
        resource_conf, cancellation_context_manager, api, logger
    )


def _set_interfaces(ifaces):
    def _ifaces():
        yield from ifaces

    return _ifaces


@pytest.mark.parametrize("is_add_floating_ip", ([True, False]))
def test_deploy(
    deploy_app_flow,
    deploy_vm_request_actions,
    is_add_floating_ip,
    api,
):
    deploy_vm_request_actions.deploy_app.add_floating_ip = is_add_floating_ip
    iface = Mock()
    ifaces = PropertyMock(side_effect=_set_interfaces([iface]))
    inst = Mock()
    type(inst).interfaces = ifaces
    api.Instance.create.return_value = inst

    result = deploy_app_flow._deploy(deploy_vm_request_actions)

    api.Instance.create.assert_called_once()
    if is_add_floating_ip:
        api.FloatingIp.create.assert_called_once()
    assert result.actionId == deploy_vm_request_actions.deploy_app.actionId
    assert result.success is True
    assert result.vmUuid == inst.id
    assert result.vmName == inst.name


def test_deploy_failed(deploy_app_flow, deploy_vm_request_actions, api):
    api.Instance.create.side_effect = ValueError("cannot create instance")

    result = deploy_app_flow._deploy(deploy_vm_request_actions)

    assert result.actionId == deploy_vm_request_actions.deploy_app.actionId
    assert result.success is False
    assert result.errorMessage == "cannot create instance"
