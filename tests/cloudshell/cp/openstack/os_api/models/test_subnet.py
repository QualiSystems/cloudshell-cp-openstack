import pytest

from cloudshell.cp.openstack.exceptions import SubnetNotFound


@pytest.fixture
def local_network(os_api_v2, neutron_emu):
    return os_api_v2.Network.create("net name")


def test_get(os_api_v2, neutron_emu, local_network):
    id_ = "id"
    name = "subnet name"
    cidr = "192.168.1.0/24"
    neutron_emu.emu_add_subnet(id_, name, local_network.id, cidr)

    subnet = os_api_v2.Subnet.get(id_)

    assert subnet.id == id_
    assert subnet.name == name
    assert subnet.network_id == local_network.id
    assert subnet.network == local_network
    assert subnet.cidr == cidr
    assert str(subnet) == f"Subnet '{name}'"


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(SubnetNotFound):
        os_api_v2.Subnet.get("missed id")


def test_find_by_network(os_api_v2, neutron_emu, local_network):
    id1, name1, cidr1 = "id1", "name1", "10.0.1.0/24"
    id2, name2, cidr2 = "id2", "name2", "10.0.2.0/24"
    neutron_emu.emu_add_subnet(id1, name1, local_network.id, cidr1)
    neutron_emu.emu_add_subnet(id2, name2, local_network.id, cidr2)

    subnets = list(os_api_v2.Subnet.find_by_network(local_network.id))

    assert len(subnets) == 2
    subnet1, subnet2 = subnets
    assert subnet1.id == id1
    assert subnet1.name == name1
    assert subnet1.cidr == cidr1
    assert subnet1.network_id == local_network.id

    assert subnet2.id == id2
    assert subnet2.name == name2
    assert subnet2.cidr == cidr2
    assert subnet2.network_id == local_network.id


def test_all(os_api_v2, neutron_emu, local_network):
    id1, name1, cidr1 = "1", "name1", "10.0.1.0/24"
    id2, name2, cidr2 = "2", "name2", "10.0.2.0/24"
    neutron_emu.emu_add_subnet(id1, name1, local_network.id, cidr1)
    neutron_emu.emu_add_subnet(id2, name2, local_network.id, cidr2)

    subnets = list(os_api_v2.Subnet.all())

    assert len(subnets) == 2
    subnet1, subnet2 = subnets

    assert subnet1.id == id1
    assert subnet1.name == name1
    assert subnet1.network_id == local_network.id
    assert subnet1.cidr == cidr1

    assert subnet2.id == id2
    assert subnet2.name == name2
    assert subnet2.network_id == local_network.id
    assert subnet2.cidr == cidr2


def test_create(os_api_v2, neutron_emu, local_network):
    subnet_name = "subnet name"
    cidr = "10.0.2.0/24"

    subnet = os_api_v2.Subnet.create(subnet_name, local_network, cidr)

    assert subnet.name == subnet_name
    assert subnet.cidr == cidr
    assert subnet.ip_version == 4
    assert subnet.network_id == local_network.id
    assert subnet.allocation_pools == []
    assert len(list(os_api_v2.Subnet.all())) == 1


def test_getting_used_cidrs(os_api_v2, neutron_emu, local_network):
    cidr1, cidr2 = "10.0.1.0/24", "10.0.2.0/24"
    neutron_emu.emu_add_subnet("id", "name", local_network.id, cidr1)
    neutron_emu.emu_add_subnet("id", "name", local_network.id, cidr2)

    cidrs = os_api_v2.Subnet.get_used_cidrs()

    assert cidrs == {cidr1, cidr2}
