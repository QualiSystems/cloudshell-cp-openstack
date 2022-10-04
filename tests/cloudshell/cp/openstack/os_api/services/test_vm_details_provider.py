from unittest.mock import Mock

from cloudshell.cp.openstack.os_api.services.vm_details_provider import create


def test_create():
    mgmt_net_id = "net id"
    iface = Mock(name="Iface", network_id=mgmt_net_id)
    inst = Mock(name="Instance", interfaces=[iface])

    data = create(inst, mgmt_net_id)

    assert data.appName == inst.name

    vm_details_map = {attr.key: attr.value for attr in data.vmInstanceData}
    assert vm_details_map == {
        "Image": inst.image.name,
        "Flavor": inst.flavor.name,
        "Availability Zone": inst.available_zone,
        "CPU": f"{inst.flavor.vcpus} vCPU",
        "Memory": f"{inst.flavor.ram_mb} MB",
        "Disk Size": f"{inst.flavor.disk_gb} GB",
    }

    assert len(data.vmNetworkData) == 1
    vm_interface = data.vmNetworkData[0]
    assert vm_interface.interfaceId == iface.mac_address
    assert vm_interface.networkId == iface.network_id
    assert vm_interface.isPrimary is True
    assert vm_interface.isPredefined is True
    assert vm_interface.privateIpAddress == iface.fixed_ip
    assert vm_interface.publicIpAddress == iface.floating_ip
    network_data_map = {attr.key: attr.value for attr in vm_interface.networkData}
    assert network_data_map == {
        "IP": iface.fixed_ip,
        "MAC Address": iface.mac_address,
        "VLAN Name": iface.network.name,
        "Floating IP": iface.floating_ip,
    }
