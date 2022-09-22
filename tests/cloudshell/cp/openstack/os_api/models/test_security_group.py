import pytest


@pytest.fixture()
def add_security_group(neutron):
    neutron.show_security_group.return_value = {
        "security_group": {"id": "sg id", "name": "sg name"}
    }


@pytest.fixture()
def sg(os_api_v2, add_security_group):
    return os_api_v2.SecurityGroup.get("sg id")


def test_create(os_api_v2, neutron):
    name = "name"
    sg_id = "sg id"
    neutron.create_security_group.return_value = {
        "security_group": {"id": sg_id, "name": name}
    }
    sg = os_api_v2.SecurityGroup.create(name)

    assert sg.id == sg_id
    assert sg.name == name
    neutron.create_security_group.assert_called_once_with(
        {"security_group": {"name": name}}
    )


def test_remove(sg, neutron):
    sg.remove()

    neutron.delete_security_group.assert_called_once_with(sg.id)


def test_add_rule(sg, neutron):
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
    neutron.create_security_group_rule.assert_called_once_with(
        {"security_group_rule": expected_data}
    )
