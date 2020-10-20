from cloudshell.cp.openstack.flows import refresh_ip


def test_refresh_ip(
    os_api, deployed_app, resource_conf, nova, neutron, instance, cs_api
):
    net_name = "net name"
    private_ip = "192.168.1.1"
    public_ip = "8.8.4.4"
    instance.addresses = {
        net_name: [{"OS-EXT-IPS:type": "fixed", "addr": private_ip}],
        "another_network": [{"OS-EXT-IPS:type": "floating", "addr": public_ip}],
    }
    neutron.list_networks.return_value = {
        "networks": [{"id": resource_conf.os_mgmt_net_id, "name": net_name}]
    }

    refresh_ip(os_api, deployed_app, resource_conf)

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)
    neutron.list_networks.assert_called_once_with(id=resource_conf.os_mgmt_net_id)
    cs_api.UpdateResourceAddress.assert_called_once_with(deployed_app.name, private_ip)
    cs_api.SetAttributeValue.assert_called_once_with(
        resourceFullPath=deployed_app.name,
        attributeName=f"{deployed_app._namespace}Public IP",
        attributeValue=public_ip,
    )
