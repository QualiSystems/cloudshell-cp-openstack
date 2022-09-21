from unittest.mock import Mock


def test_create(os_api_v2, neutron):
    floating_net_id = "floating net id"
    floating_subnet_id = "floating subnet id"
    floating_subnet = Mock(
        name="subnet", network_id=floating_net_id, id=floating_subnet_id
    )
    port_id = "port id"
    port = Mock(name="port", id=port_id)
    floating_ip = "192.168.105.73"
    neutron.create_floatingip.return_value = {
        "floatingip": {"id": "id", "floating_ip_address": floating_ip}
    }

    ip = os_api_v2.FloatingIp.create(floating_subnet, port)

    assert ip.ip_address == floating_ip
    neutron.create_floatingip.assert_called_once_with(
        {
            "floatingip": {
                "floating_network_id": floating_net_id,
                "subnet_id": floating_subnet_id,
                "port_id": port_id,
            }
        }
    )
