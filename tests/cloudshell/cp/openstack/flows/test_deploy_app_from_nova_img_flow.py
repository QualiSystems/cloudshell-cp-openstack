import pytest

from cloudshell.cp.openstack.flows import DeployAppFromNovaImgFlow


@pytest.fixture()
def deploy_app_flow(resource_conf, cancellation_context_manager, os_api, logger):
    return DeployAppFromNovaImgFlow(
        resource_conf, cancellation_context_manager, os_api, logger
    )


@pytest.mark.parametrize("is_add_floating_ip", ([True, False]))
def test_deploy(
    deploy_app_flow,
    deploy_vm_request_actions,
    nova,
    neutron,
    instance,
    is_add_floating_ip,
):
    deploy_vm_request_actions.deploy_app.add_floating_ip = is_add_floating_ip

    result = deploy_app_flow._deploy(deploy_vm_request_actions)

    nova.servers.create.assert_called_once()
    if is_add_floating_ip:
        neutron.create_floatingip.assert_called_once()
    neutron.list_networks.assert_called_once_with(
        id=deploy_app_flow._resource_conf.os_mgmt_net_id
    )
    assert result.actionId == deploy_vm_request_actions.deploy_app.actionId
    assert result.success is True
    assert result.vmUuid == instance.id
    assert result.vmName == instance.name


def test_deploy_failed(deploy_app_flow, deploy_vm_request_actions, nova):
    nova.servers.create.side_effect = ValueError("cannot create instance")

    result = deploy_app_flow._deploy(deploy_vm_request_actions)

    assert result.actionId == deploy_vm_request_actions.deploy_app.actionId
    assert result.success is False
    assert result.errorMessage == "cannot create instance"
