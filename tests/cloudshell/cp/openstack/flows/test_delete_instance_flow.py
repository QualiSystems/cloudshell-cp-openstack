from unittest.mock import Mock, call

import pytest

from cloudshell.cp.openstack.flows import delete_instance


@pytest.fixture
def api():
    return Mock(name="OS API")


@pytest.fixture
def inst(api):
    inst = Mock(name="inst")
    api.Instance.get.return_value = inst
    return inst


@pytest.fixture
def mgmt_iface(inst):
    iface = Mock(name="mgmt-iface")
    inst.find_interface_by_port_name.return_value = iface
    return iface


@pytest.fixture
def inst_sg(inst):
    sg = Mock(name="Security Group")
    inst.find_security_group.return_value = sg
    return sg


def test_delete(api, deployed_app, inst, mgmt_iface, inst_sg):
    delete_instance(api, deployed_app)

    api.assert_has_calls([call.Instance.get(deployed_app.vmdetails.uid)])
    inst.assert_has_calls(
        [
            call.find_interface_by_port_name("mgmt-port"),
            call.find_security_group(f"sg-{inst.name}"),
            call.remove_security_group(inst_sg),
            call.remove(),
        ]
    )
    mgmt_iface.assert_has_calls(
        [
            call.api.FloatingIp.find_by_ip(mgmt_iface.floating_ip).remove(),
            call.port.remove(),
        ]
    )
    inst_sg.assert_has_calls([call.remove()])
