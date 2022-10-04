import pytest

from cloudshell.cp.openstack.exceptions import SecurityGroupNotFound


@pytest.fixture()
def sg(os_api_v2, neutron_emu):
    return os_api_v2.SecurityGroup.create("default")


def test_get(os_api_v2, neutron_emu):
    id_, name = "id", "name"
    neutron_emu.emu_add_security_group(id_, name)

    sg = os_api_v2.SecurityGroup.get(id_)

    assert sg.id == id_
    assert sg.name == name
    assert str(sg) == f"Security Group '{name}'"


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(SecurityGroupNotFound):
        os_api_v2.SecurityGroup.get("missed id")


def test_all(os_api_v2, neutron_emu):
    id1, name1 = "id1", "name1"
    id2, name2 = "id2", "name2"
    neutron_emu.emu_add_security_group(id1, name1)
    neutron_emu.emu_add_security_group(id2, name2)

    sgs = list(os_api_v2.SecurityGroup.all())
    assert len(sgs) == 2
    sg1, sg2 = sgs

    assert sg1.id == id1
    assert sg1.name == name1
    assert sg2.id == id2
    assert sg2.name == name2


def test_create(os_api_v2, neutron_emu):
    name = "name"

    sg = os_api_v2.SecurityGroup.create(name)

    assert sg.name == name
    assert len(list(os_api_v2.SecurityGroup.all())) == 1


def test_remove(os_api_v2, sg):
    sg.remove()
    sg.remove()  # ignores not found

    assert len(list(os_api_v2.SecurityGroup.all())) == 0


def test_add_rule(sg, neutron_emu):
    cidr = "10.0.0.0/24"
    protocol = "tcp"
    port_min = port_max = 22
    direction = "ingress"

    sg.add_rule(
        cidr=cidr,
        protocol=protocol,
        port_range_min=port_min,
        port_range_max=port_max,
        direction=direction,
    )

    expected_data = {
        "remote_ip_prefix": cidr,
        "port_range_min": port_min,
        "port_range_max": port_max,
        "protocol": protocol,
        "security_group_id": sg.id,
        "direction": direction,
    }
    assert neutron_emu.emu_security_group_rules[0] == expected_data
    assert len(neutron_emu.emu_security_group_rules) == 1
