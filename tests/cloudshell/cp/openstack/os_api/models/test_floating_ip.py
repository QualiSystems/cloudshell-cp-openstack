import pytest

from cloudshell.cp.openstack.exceptions import FloatingIpNotFound


def test_get(os_api_v2, neutron_emu):
    id_, ip = "id", "192.168.105.12"
    neutron_emu.emu_add_floating_ip(id_, ip)

    fip = os_api_v2.FloatingIp.get(id_)

    assert fip.id == id_
    assert fip.ip_address == ip


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(FloatingIpNotFound):
        os_api_v2.FloatingIp.get("missed id")


def test_find_by_ip(os_api_v2, neutron_emu):
    id_, ip = "id", "192.168.105.13"
    neutron_emu.emu_add_floating_ip(id_, ip)

    fip = os_api_v2.FloatingIp.find_by_ip(ip)

    assert fip.id == id_
    assert fip.ip_address == ip


def test_find_by_ip_not_found(os_api_v2, neutron_emu):
    with pytest.raises(FloatingIpNotFound):
        os_api_v2.FloatingIp.find_by_ip("192.168.1.1")


def test_all(os_api_v2, neutron_emu):
    id1, ip1 = "id1", "192.168.113.11"
    id2, ip2 = "id2", "192.168.113.12"
    neutron_emu.emu_add_floating_ip(id1, ip1)
    neutron_emu.emu_add_floating_ip(id2, ip2)

    fips = list(os_api_v2.FloatingIp.all())
    assert len(fips) == 2
    fip1, fip2 = fips

    assert fip1.id == id1
    assert fip1.ip_address == ip1

    assert fip2.id == id2
    assert fip2.ip_address == ip2


def test_create(os_api_v2, neutron_emu, local_network):
    port = os_api_v2.Port.create("port name", local_network)
    ip = "192.168.1.13"
    subnet = next(local_network.subnets)

    fip = os_api_v2.FloatingIp.create(subnet, port)

    assert fip.ip_address == ip


def test_remove(os_api_v2, neutron_emu):
    id_, ip = "id", "192.168.105.13"
    neutron_emu.emu_add_floating_ip(id_, ip)

    fip = os_api_v2.FloatingIp.get(id_)
    fip.remove()
    fip.remove()  # ignore not found

    assert len(list(os_api_v2.FloatingIp.all())) == 0
