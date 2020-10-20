import pytest

from cloudshell.cp.openstack.flows import PowerFlow


@pytest.fixture()
def power_flow(os_api, deployed_app, logger):
    return PowerFlow(os_api, deployed_app, logger)


def test_power_on(power_flow, nova, deployed_app, instance):
    instance.status = ["building", "building", "active", "active"]

    power_flow.power_on()

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)
    instance.start.assert_called_once_with()
    instance.get.assert_called_once_with()


def test_power_off(power_flow, nova, deployed_app, instance):
    instance.status = ["active", "active", "shutoff", "shutoff"]

    power_flow.power_off()

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)
    instance.stop.assert_called_once_with()
    instance.get.assert_called_once_with()
