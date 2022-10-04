import pytest
from neutronclient.common import exceptions as neutron_exc

from cloudshell.cp.openstack.exceptions import TrunkNotFound
from cloudshell.cp.openstack.os_api.models import NetworkType


@pytest.fixture
def port(os_api_v2, neutron_emu, local_network):
    return os_api_v2.Port.create("port name", local_network)


def test_get(os_api_v2, neutron_emu, port):
    id_, name = "id", "name"
    neutron_emu.emu_add_trunk(id_, name, port.id)

    trunk = os_api_v2.Trunk.get(id_)

    assert trunk.id == id_
    assert trunk.name == name
    assert trunk.port_id == port.id
    assert trunk.port == port
    assert str(trunk) == f"Trunk '{name}'"


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(TrunkNotFound):
        os_api_v2.Trunk.get("missed id")


def test_find_by_name(os_api_v2, neutron_emu, port):
    id_, name = "id", "name"
    neutron_emu.emu_add_trunk(id_, name, port.id)

    trunk = os_api_v2.Trunk.find_first(name)

    assert trunk.id == id_
    assert trunk.name == name


def test_find_by_name_not_found(os_api_v2, neutron_emu):
    with pytest.raises(TrunkNotFound):
        os_api_v2.Trunk.find_first("missed name")


def test_all(os_api_v2, neutron_emu, port):
    id1, name1 = "id1", "name1"
    id2, name2 = "id2", "name2"
    neutron_emu.emu_add_trunk(id1, name1, port.id)
    neutron_emu.emu_add_trunk(id2, name2, port.id)

    trunks = list(os_api_v2.Trunk.all())
    assert len(trunks)
    trunk1, trunk2 = trunks

    assert trunk1.id == id1
    assert trunk1.name == name1

    assert trunk2.id == id2
    assert trunk2.name == name2


def test_create(os_api_v2, neutron_emu, port):
    name = "name"

    trunk = os_api_v2.Trunk.create(name, port)

    assert trunk.name == name
    assert len(list(os_api_v2.Trunk.all())) == 1


def test_find_or_create(os_api_v2, neutron_emu, port):
    name = "name"

    created_trunk = os_api_v2.Trunk.find_or_create(name, port)
    assert len(list(os_api_v2.Trunk.all())) == 1

    found_trunk = os_api_v2.Trunk.find_or_create(name, port)
    assert len(list(os_api_v2.Trunk.all())) == 1
    assert created_trunk == found_trunk
    assert created_trunk.name == found_trunk.name == name


def test_remove(os_api_v2, neutron_emu, port):
    trunk = os_api_v2.Trunk.create("name", port)

    trunk.remove()
    trunk.remove()  # ignore removed
    assert len(list(os_api_v2.Trunk.all())) == 0


def test_sub_ports(os_api_v2, neutron_emu, port):
    vlan13 = os_api_v2.Network.create(
        "net13", vlan_id=13, network_type=NetworkType.VXLAN
    )
    vlan14 = os_api_v2.Network.create(
        "net14", vlan_id=14, network_type=NetworkType.VXLAN
    )
    sub_port1 = os_api_v2.Port.create("name1", vlan13, port.mac_address)
    sub_port2 = os_api_v2.Port.create("name2", vlan14, port.mac_address)
    trunk = os_api_v2.Trunk.create("trunk name", port)

    trunk.add_sub_port(sub_port1)
    trunk.add_sub_port(sub_port2)

    subports = list(trunk.sub_ports)
    assert len(subports) == 2

    assert subports[0] == sub_port1
    assert subports[1] == sub_port2

    trunk.remove_sub_port(sub_port1)
    trunk.remove_sub_port(sub_port2)

    assert len(list(trunk.sub_ports)) == 0


def test_getting_subports_trunk_removed(os_api_v2, neutron_emu, port):
    trunk = os_api_v2.Trunk.create("name", port)
    trunk.remove()

    with pytest.raises(TrunkNotFound):
        _ = trunk.sub_ports_ids


def test_adding_sub_port_that_already_added(
    os_api_v2, neutron_emu, port, local_network
):
    vlan13 = os_api_v2.Network.create(
        "net13", vlan_id=13, network_type=NetworkType.VXLAN
    )
    sub_port1 = os_api_v2.Port.create("name1", vlan13, port.mac_address)
    trunk = os_api_v2.Trunk.create("trunk name", port)

    trunk.add_sub_port(sub_port1)
    trunk.add_sub_port(sub_port1)  # ignores

    another_port = os_api_v2.Port.create("another port", local_network)
    another_trunk = os_api_v2.Trunk.create("another trunk", another_port)

    with pytest.raises(neutron_exc.Conflict):
        another_trunk.add_sub_port(sub_port1)
