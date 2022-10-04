from unittest.mock import Mock

import pytest
from neutronclient.common import exceptions as neutron_exc

from cloudshell.cp.openstack.exceptions import PortIsNotGone, PortNotFound


def test_get(os_api_v2, neutron_emu, local_network):
    id_, name, net_id, mac = "id", "name", local_network.id, "mac"
    neutron_emu.emu_add_port(id_, name, net_id, mac)

    port = os_api_v2.Port.get(id_)

    assert port.id == id_
    assert port.name == name
    assert port.network_id == net_id
    assert port.network == local_network
    assert port.mac_address == mac
    assert port.trunk is None
    assert str(port) == f"Port '{name}'"


def test_get_not_found(os_api_v2, neutron_emu):
    with pytest.raises(PortNotFound):
        os_api_v2.Port.get("missed ip")


def test_find_by_name(os_api_v2, neutron_emu, local_network):
    id_, name = "id", "port name"
    neutron_emu.emu_add_port(id_, name, local_network.id)

    port = os_api_v2.Port.find_first(name)

    assert port.id == id_
    assert port.name == name


def test_find_by_name_not_found(os_api_v2, neutron_emu):
    with pytest.raises(PortNotFound):
        os_api_v2.Port.find_first("missed name")


def test_all(os_api_v2, neutron_emu, local_network):
    id1, name1 = "id1", "name1"
    id2, name2 = "id2", "name2"
    neutron_emu.emu_add_port(id1, name1, local_network.id)
    neutron_emu.emu_add_port(id2, name2, local_network.id)

    ports = list(os_api_v2.Port.all())
    assert len(ports) == 2
    port1, port2 = ports

    assert port1.id == id1
    assert port1.name == name1

    assert port2.id == id2
    assert port2.name == name2


def test_create(os_api_v2, neutron_emu, local_network):
    name, mac = "name", "mac"
    subnet = next(local_network.subnets)

    port = os_api_v2.Port.create(
        name,
        local_network,
        mac_address=mac,
        fixed_ip="192.168.1.13",
        fixed_ip_subnet=subnet,
    )

    assert port.name == name
    assert port.mac_address == mac
    assert port.network_id == local_network.id
    assert len(list(os_api_v2.Port.all())) == 1


def test_find_or_create(os_api_v2, neutron_emu, local_network):
    name = "name"

    port_created = os_api_v2.Port.find_or_create(name, local_network)
    assert len(list(os_api_v2.Port.all())) == 1

    port_found = os_api_v2.Port.find_or_create(name, local_network)
    assert len(list(os_api_v2.Port.all())) == 1
    assert port_created == port_found


def test_with_trunk(os_api_v2, neutron_emu, local_network):
    port_id = "port id"
    neutron_emu.emu_add_port(port_id, "port name", local_network.id)
    neutron_emu.emu_add_trunk("trunk id", "trunk name", port_id)

    port = os_api_v2.Port.get(port_id)
    assert port.trunk
    trunk = port.trunk
    assert trunk.port_id == port_id
    assert trunk.id == "trunk id"
    assert trunk.name == "trunk name"


def test_remove(os_api_v2, neutron_emu, local_network):
    port_id = "port id"
    neutron_emu.emu_add_port(port_id, "port name", local_network.id)

    port = os_api_v2.Port.get(port_id)
    port.remove()
    port.remove()  # ignore port not found

    assert len(list(os_api_v2.Port.all())) == 0


def test_wait_until_is_gone(os_api_v2, neutron_emu, local_network):
    port = os_api_v2.Port.create("name", local_network)
    port_data = neutron_emu.show_port(port.id)
    neutron_emu.show_port = Mock(side_effect=[port_data] * 5)

    with pytest.raises(PortIsNotGone):
        port.wait_until_is_gone(timeout=5)

    neutron_emu.show_port = Mock(side_effect=neutron_exc.PortNotFoundClient)
    port.wait_until_is_gone()


def test_update_port_name(os_api_v2, neutron_emu, local_network):
    port_name = "port name"
    port = os_api_v2.Port.create(port_name, local_network)

    assert port.name == port_name

    new_port_name = "new port name"
    port.name = new_port_name
    assert port.name == new_port_name

    assert os_api_v2.Port.get(port.id).name == new_port_name
