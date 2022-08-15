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
    }
    neutron.create_subnet.assert_called_once_with({"subnet": data})
    assert subnet == os_api_v2.Subnet.from_dict(neutron.create_subnet()["subnet"])
