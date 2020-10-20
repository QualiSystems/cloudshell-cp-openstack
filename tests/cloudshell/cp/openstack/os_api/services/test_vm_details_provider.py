from unittest.mock import Mock

from cloudshell.cp.openstack.os_api.services.vm_details_provider import create


def test_create(instance, os_api, neutron):
    net_id = "net id"
    interface = Mock(net_id=net_id)
    instance.interface_list.return_value = [interface]
    interface_network_name = "net name"
    interface_vlan_id = "vlan id"
    private_ip = "192.168.1.1"
    public_ip = "8.8.8.8"
    instance.addresses = {
        interface_network_name: [
            {"addr": private_ip, "OS-EXT-IPS:type": "fixed"},
            {"addr": public_ip, "OS-EXT-IPS:type": "floating"},
        ]
    }
    neutron.list_networks.return_value = {
        "networks": [
            {
                "name": interface_network_name,
                "provider:segmentation_id": interface_vlan_id,
            }
        ]
    }

    data = create(instance, os_api, net_id)

    instance.get.assert_called_once_with()  # update instance data
    assert data.appName == instance.name

    vm_details_map = {attr.key: attr.value for attr in data.vmInstanceData}
    flavor = os_api.get_flavor_from_instance(instance)
    assert vm_details_map == {
        "Image": os_api.get_image_from_instance(instance).name,
        "Flavor": flavor.name,
        "Availability Zone": getattr(instance, "OS-EXT-AZ:availability_zone"),
        "CPU": f"{flavor.vcpus} vCPU",
        "Memory": f"{flavor.ram} GB",
        "Disk Size": f"{flavor.disk} GB",
    }

    assert len(data.vmNetworkData) == 1
    vm_interface = data.vmNetworkData[0]
    assert vm_interface.interfaceId == interface.mac_addr
    assert vm_interface.networkId == interface_vlan_id
    assert vm_interface.isPrimary is True
    assert vm_interface.isPredefined is True
    assert vm_interface.privateIpAddress == private_ip
    assert vm_interface.publicIpAddress == public_ip
    network_data_map = {attr.key: attr.value for attr in vm_interface.networkData}
    assert network_data_map == {
        "IP": private_ip,
        "MAC Address": interface.mac_addr,
        "VLAN Name": interface_network_name,
        "Floating IP": public_ip,
    }
