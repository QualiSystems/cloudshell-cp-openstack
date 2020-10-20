from unittest.mock import patch

import pytest

from cloudshell.cp.openstack.flows import GetVMDetailsFlow


@pytest.fixture()
def get_vm_details_flow(os_api, resource_conf, cancellation_context_manager, logger):
    return GetVMDetailsFlow(resource_conf, cancellation_context_manager, os_api, logger)


def test_get_vm_details(get_vm_details_flow, deployed_app, nova, instance):
    with patch(
        "cloudshell.cp.openstack.flows.vm_details.vm_details_provider.create"
    ) as vm_details_mock:
        result = get_vm_details_flow._get_vm_details(deployed_app)

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)
    vm_details_mock.assert_called_once_with(
        instance,
        get_vm_details_flow._api,
        get_vm_details_flow._resource_config.os_mgmt_net_id,
    )
    assert result == vm_details_mock()


def test_get_vm_details_failed(get_vm_details_flow, deployed_app, instance):
    with patch(
        "cloudshell.cp.openstack.flows.vm_details.vm_details_provider.create"
    ) as vm_details_mock:
        vm_details_mock.side_effect = ValueError("error getting vm details")
        result = get_vm_details_flow._get_vm_details(deployed_app)

    assert result.errorMessage == "error getting vm details"
    assert result.appName == instance.name
