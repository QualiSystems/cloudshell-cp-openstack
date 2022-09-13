def test_create_subnet(os_api_v2, neutron, simple_network):
    subnet_name = "subnet name"
    cidr = "10.0.2.0/24"

    subnet = os_api_v2.Subnet.create(subnet_name, simple_network, cidr)

    data = {
        "name": subnet_name,
        "network_id": simple_network.id,
        "cidr": cidr,
        "ip_version": 4,
        "gateway_ip": None,
        "allocation_pools": [],
    }
    neutron.create_subnet.assert_called_once_with({"subnet": data})
    assert subnet == os_api_v2.Subnet.from_dict(neutron.create_subnet()["subnet"])


def test_get_subnet(os_api_v2, neutron, simple_network):
    subnet_id = "subnet id"
    subnet_name = "subnet name"
    cidr = "192.168.1.0/24"
    neutron.show_subnet.return_value = {
        "subnet": {
            "id": subnet_id,
            "name": subnet_name,
            "network_id": simple_network.id,
            "ip_version": 4,
            "cidr": cidr,
            "gateway_ip": None,
            "allocation_pools": [{"start": "192.168.1.1", "end": "192.168.1.254"}],
        }
    }
    neutron.show_network.return_value = {
        "network": {
            "id": simple_network.id,
            "name": simple_network.name,
            "provider:network_type": simple_network.network_type.value,
            "provider:segmentation_id": simple_network.vlan_id,
        }
    }

    subnet = os_api_v2.Subnet.get(subnet_id)

    assert subnet.id == subnet_id
    assert subnet.name == subnet_name
    assert subnet.network_id == simple_network.id
    assert subnet.cidr == cidr
    assert str(subnet) == f"Subnet '{subnet_name}'"

    assert subnet.network == simple_network
    neutron.show_network.assert_called_once_with(simple_network.id)
