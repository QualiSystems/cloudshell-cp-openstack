from unittest.mock import Mock, call

import pytest

from cloudshell.cp.openstack.flows import refresh_ip


@pytest.fixture()
def api():
    return Mock(name="OS API")


def test_refresh_ip(api, deployed_app, resource_conf, nova, neutron, instance, cs_api):
    private_ip = "192.168.1.1"
    public_ip = "8.8.4.4"
    mgmt_iface = Mock(name="mgmt-iface", fixed_ip=private_ip, floating_ip=public_ip)

    def _find_iface(name):
        assert name == "mgmt-port"
        return mgmt_iface

    api.Instance.get.return_value = Mock(find_interface_by_port_name=_find_iface)

    refresh_ip(api, deployed_app, resource_conf)

    api.assert_has_calls((call.Instance.get(deployed_app.vmdetails.uid),))
    cs_api.UpdateResourceAddress.assert_called_once_with(deployed_app.name, private_ip)
    cs_api.SetAttributeValue.assert_called_once_with(
        resourceFullPath=deployed_app.name,
        attributeName=f"{deployed_app._namespace}Public IP",
        attributeValue=public_ip,
    )
