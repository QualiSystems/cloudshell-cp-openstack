import pytest

from cloudshell.cp.openstack.exceptions import NetworkInUse, NetworkNotFound
from cloudshell.cp.openstack.os_api.models import NetworkType


def test_network_type():
    net_type = NetworkType("LOCAL")

    assert net_type is NetworkType.LOCAL


def test_get(os_api_v2, neutron_emu):
    net_id = "net id"
    name = "net name"
    net_type = NetworkType.VXLAN
    vlan_id = 101
    external = True
    neutron_emu.emu_add_network(net_id, name, net_type, vlan_id, external)

    net = os_api_v2.Network.get(net_id)

    assert net.id == net_id
    assert net.name == name
    assert net.network_type == net_type
    assert net.vlan_id == vlan_id
    assert net.is_external is external
    assert str(net) == f"Network '{name}'"


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(NetworkNotFound):
        os_api_v2.Network.get("missed id")


def test_find_by_name(os_api_v2, neutron_emu):
    neutron_emu.emu_add_network("id", name="Local")
    neutron_emu.emu_add_network("id", name="Local")

    net = os_api_v2.Network.find_first("Local")

    assert net.name == "Local"


def test_find_by_name_not_found(os_api_v2, neutron_emu):
    with pytest.raises(NetworkNotFound):
        os_api_v2.Network.find_first("missed network name")


def test_find_by_vlan_id(os_api_v2, neutron_emu):
    neutron_emu.emu_add_network("id", name="vlan13", vlan_id=13)

    net = os_api_v2.Network.find_by_vlan_id(13)

    assert net.vlan_id == 13
    assert net.name == "vlan13"


def test_find_by_vlan_id_not_found(os_api_v2, neutron_emu):
    with pytest.raises(NetworkNotFound):
        os_api_v2.Network.find_by_vlan_id(11)


def test_all(os_api_v2, neutron_emu):
    id1, name1 = "1", "name1"
    id2, name2 = "2", "name2"
    neutron_emu.emu_add_network(id1, name1)
    neutron_emu.emu_add_network(id2, name2)

    networks = list(os_api_v2.Network.all())

    assert len(networks) == 2
    net1, net2 = networks
    assert net1.id == id1
    assert net1.name == name1
    assert net2.id == id2
    assert net2.name == name2


def test_create(os_api_v2, neutron_emu):
    name = "net name"
    vlan_id = 12
    net_type = NetworkType.VLAN
    qnq = True
    physical_iface = "iface"

    net = os_api_v2.Network.create(
        name,
        vlan_id=vlan_id,
        network_type=net_type,
        qnq=qnq,
        physical_iface_name=physical_iface,
    )

    assert net.name == name
    assert net.vlan_id == vlan_id
    assert net.network_type == net_type
    assert net.is_external is False
    assert len(list(os_api_v2.Network.all())) == 1


def test_remove(os_api_v2, neutron_emu):
    neutron_emu.emu_add_network("id1", "name1")

    net = os_api_v2.Network.get("id1")
    net.remove()

    assert len(list(os_api_v2.Network.all())) == 0


def test_remove_not_found(os_api_v2, neutron_emu):
    neutron_emu.emu_add_network("id1", "name1")

    net = os_api_v2.Network.get("id1")
    net.remove()
    net.remove()  # trying to remove after it's already removed

    assert len(list(os_api_v2.Network.all())) == 0


def test_remove_in_use(os_api_v2, neutron_emu):
    neutron_emu.emu_add_network("id1", "net1", in_use=True)

    net = os_api_v2.Network.get("id1")

    with pytest.raises(NetworkInUse):
        net.remove(raise_in_use=True)
    assert len(list(os_api_v2.Network.all())) == 1

    net.remove(raise_in_use=False)
    assert len(list(os_api_v2.Network.all())) == 1


def test_getting_subnet(os_api_v2, neutron_emu):
    net_id = "net id"
    name = "net name"
    neutron_emu.emu_add_network(net_id, name)
    sub_id = "sub id"
    sub_name = "sub name"
    cidr = "192.168.10.0/24"
    neutron_emu.emu_add_subnet(sub_id, sub_name, net_id, cidr)

    net = os_api_v2.Network.get(net_id)

    assert net.id == net_id
    assert net.name == name

    subnets = list(net.subnets)
    assert len(subnets) == 1
    subnet = subnets[0]

    assert subnet.id == sub_id
    assert subnet.name == sub_name
    assert subnet.network_id == net_id
    assert subnet.cidr == cidr
