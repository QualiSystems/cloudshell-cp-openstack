from unittest.mock import Mock

from cloudshell.cp.openstack.flows import delete_instance


def test_delete_instance(os_api, deployed_app, nova, neutron, instance):
    sg = Mock(id="sg id")
    sg.name = f"sg-{instance.name}"
    instance.list_security_group.return_value = [sg]
    delete_instance(os_api, deployed_app)

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)

    neutron.list_floatingips.assert_called_once_with(
        floating_ip_address=deployed_app.public_ip
    )
    neutron.delete_floatingip(neutron.list_floatingips()["floatingips"][0]["id"])

    instance.list_security_group.assert_called_once()
    neutron.delete_security_group.assert_called_once_with("sg id")

    instance.delete.assert_called_once()
