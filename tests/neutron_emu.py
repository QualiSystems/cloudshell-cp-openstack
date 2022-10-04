from __future__ import annotations

from uuid import uuid4

from neutronclient.common import exceptions as neutron_exc

from cloudshell.cp.openstack.os_api.models import NetworkType


def get_network_data(
    id_: str,
    name: str,
    net_type: NetworkType,
    vlan_id: int | None,
    external: bool,
    in_use: bool,
) -> dict:
    return {
        "id": id_,
        "name": name,
        "provider:network_type": net_type.value,
        "provider:segmentation_id": vlan_id,
        "router:external": external,
        "__in_use": in_use,
    }


def get_subnet_data(
    id_: str,
    name: str,
    net_id: str,
    cidr: str,
    ip_version: int,
    gateway: str | None,
    allocation_pools: list[tuple[str, str]],
) -> dict:
    return {
        "id": id_,
        "name": name,
        "network_id": net_id,
        "ip_version": ip_version,
        "cidr": cidr,
        "gateway_ip": gateway,
        "allocation_pools": allocation_pools,
    }


def get_floating_ip_data(id_: str, ip: str) -> dict:
    return {"id": id_, "floating_ip_address": ip}


def get_port_data(id_: str, name: str, network_id: str, mac_address: str) -> dict:
    return {
        "id": id_,
        "name": name,
        "network_id": network_id,
        "mac_address": mac_address,
    }


def get_trunk_data(id_: str, name: str, port_id: str) -> dict:
    return {"id": id_, "name": name, "port_id": port_id}


def get_trunk_sub_port_data(port_id: str, vlan_id: int, segmentation_type: str) -> dict:
    return {
        "port_id": port_id,
        "segmentation_id": vlan_id,
        "segmentation_type": segmentation_type,
    }


def get_security_group_data(id_: str, name: str) -> dict:
    return {"id": id_, "name": name}


class NeutronEmu:
    def __init__(self):
        self.emu_networks: list[dict] = []
        self.emu_subnets: list[dict] = []
        self.emu_floating_ips: list[dict] = []
        self.emu_ports: list[dict] = []
        self.emu_trunks: list[dict] = []
        self.emu_trunk_subports: dict[str, list[dict[str, str]]] = {}
        self.emu_security_groups: list[dict] = []
        self.emu_security_group_rules: list[dict] = []

    def emu_add_network(
        self,
        id_: str,
        name: str,
        net_type: NetworkType = NetworkType.VXLAN,
        vlan_id: int | None = None,
        external: bool = False,
        in_use: bool = False,
    ):
        data = get_network_data(id_, name, net_type, vlan_id, external, in_use)
        self.emu_networks.append(data)

    def show_network(self, id_: str) -> dict:
        for data in self.emu_networks:
            if data["id"] == id_:
                return {"network": data}
        raise neutron_exc.NetworkNotFoundClient

    def list_networks(self, **kwargs) -> dict[str, list[dict]]:
        if not kwargs:
            data_list = self.emu_networks
        else:
            data_list = []
            for data in self.emu_networks:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"networks": data_list}

    def create_network(self, data_dict: dict) -> dict:
        data: dict = data_dict["network"]

        data.setdefault("router:external", False)
        data.setdefault("provider:network_type", NetworkType.LOCAL)
        data.setdefault("provider:segmentation_id", None)
        data["id"] = f"{data['name']}-id"
        data["__in_use"] = False
        self.emu_networks.append(data)

        return data_dict

    def delete_network(self, id_: str) -> None:
        net_dict = self.show_network(id_)
        if net_dict["network"]["__in_use"]:
            raise neutron_exc.NetworkInUseClient
        for subnet in self.emu_subnets.copy():
            if subnet["network_id"] == id_:
                self.emu_subnets.remove(subnet)
        self.emu_networks.remove(net_dict["network"])

    def emu_add_subnet(
        self,
        id_: str,
        name: str,
        net_id: str,
        cidr: str,
        ip_version: int = 4,
        gateway: str | None = None,
        allocation_pools: list[tuple[str, str]] | None = None,
    ):
        allocation_pools = allocation_pools or []
        data = get_subnet_data(
            id_, name, net_id, cidr, ip_version, gateway, allocation_pools
        )
        self.emu_subnets.append(data)

    def show_subnet(self, id_: str) -> dict:
        for data in self.emu_subnets:
            if data["id"] == id_:
                return {"subnet": data}
        raise neutron_exc.NotFound

    def list_subnets(self, **kwargs) -> dict[str, list[dict]]:
        _ = kwargs.pop("fields", [])
        if not kwargs:
            data_list = self.emu_subnets
        else:
            data_list = []
            for data in self.emu_subnets:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"subnets": data_list}

    def create_subnet(self, data_dict: dict) -> dict:
        data: dict = data_dict["subnet"]

        data["id"] = f"{data['name']}-id"
        self.emu_subnets.append(data)

        return data_dict

    def emu_add_floating_ip(self, id_: str, ip: str):
        data = get_floating_ip_data(id_, ip)
        self.emu_floating_ips.append(data)

    def show_floatingip(self, id_: str) -> dict:
        for data in self.emu_floating_ips:
            if data["id"] == id_:
                return {"floatingip": data}
        raise neutron_exc.NotFound

    def list_floatingips(self, **kwargs) -> dict[str, list[dict]]:
        _ = kwargs.pop("fields", [])
        if not kwargs:
            data_list = self.emu_floating_ips
        else:
            data_list = []
            for data in self.emu_floating_ips:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"floatingips": data_list}

    def create_floatingip(self, data_dict: dict[str, dict]) -> dict:
        data = data_dict["floatingip"]
        cidr = self.show_subnet(data["subnet_id"])["subnet"]["cidr"]
        ip = cidr.split("/", 1)[0].replace(".0", ".13")

        data["id"] = uuid4()
        data["floating_ip_address"] = ip
        self.emu_floating_ips.append(data)

        return data_dict

    def delete_floatingip(self, id_: str) -> None:
        data = self.show_floatingip(id_)["floatingip"]
        self.emu_floating_ips.remove(data)

    def emu_add_port(
        self, id_: str, name: str, net_id: str, mac: str | None = None
    ) -> None:
        mac = mac or str(uuid4())
        data = get_port_data(id_, name, net_id, mac)
        self.emu_ports.append(data)

    def show_port(self, id_: str) -> dict:
        for data in self.emu_ports:
            if data["id"] == id_:
                return {"port": data}
        raise neutron_exc.PortNotFoundClient

    def list_ports(self, **kwargs) -> dict[str, list[dict]]:
        if not kwargs:
            data_list = self.emu_ports
        else:
            data_list = []
            for data in self.emu_ports:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"ports": data_list}

    def create_port(self, data_dict: dict) -> dict:
        data: dict = data_dict["port"]

        data["id"] = f"{data['name']}-id"
        self.emu_ports.append(data)

        return data_dict

    def update_port(self, id_: str, data_dict: dict) -> None:
        new_data = data_dict["port"]
        old_data = self.show_port(id_)["port"]
        old_data.update(new_data)

    def delete_port(self, id_: str) -> None:
        data = self.show_port(id_)["port"]
        self.emu_ports.remove(data)

    def emu_add_trunk(self, id_: str, name: str, port_id: str) -> None:
        data = get_trunk_data(id_, name, port_id)
        port_data = self.show_port(port_id)["port"]
        port_data["trunk_details"] = {"trunk_id": id_}
        self.emu_trunks.append(data)

    def show_trunk(self, id_: str) -> dict:
        for data in self.emu_trunks:
            if data["id"] == id_:
                return {"trunk": data}
        raise neutron_exc.NotFound

    def list_trunks(self, **kwargs) -> dict[str, list[dict]]:
        if not kwargs:
            data_list = self.emu_trunks
        else:
            data_list = []
            for data in self.emu_trunks:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"trunks": data_list}

    def create_trunk(self, data_dict: dict) -> dict:
        data: dict = data_dict["trunk"]

        data["id"] = f"{data['name']}-id"
        self.emu_trunks.append(data)

        return data_dict

    def delete_trunk(self, id_: str) -> None:
        data = self.show_trunk(id_)["trunk"]
        self.emu_trunks.remove(data)

    def emu_add_trunk_sub_port(
        self, trunk_id: str, port_id: str, vlan_id: int, segmentation_type: str
    ):
        data = get_trunk_sub_port_data(port_id, vlan_id, segmentation_type)
        self.emu_trunk_subports.setdefault(trunk_id, []).append(data)

    def trunk_get_subports(self, trunk_id: str) -> dict[str, list[dict]]:
        _ = self.show_trunk(trunk_id)
        try:
            sub_port_dicts = self.emu_trunk_subports[trunk_id]
        except KeyError:
            sub_port_dicts = []
        return {"sub_ports": sub_port_dicts}

    def trunk_add_subports(self, trunk_id: str, data_dict: dict[str, list[dict]]):
        data = data_dict["sub_ports"][0]

        for existed_trunk_id, existed_sub_ports in self.emu_trunk_subports.items():
            for sub_ports_data in existed_sub_ports:
                if sub_ports_data["port_id"] == data["port_id"]:
                    raise neutron_exc.Conflict

        self.emu_trunk_subports.setdefault(trunk_id, []).append(data)

    def trunk_remove_subports(self, trunk_id: str, data_dict: dict[str, list[dict]]):
        port_id = data_dict["sub_ports"][0]["port_id"]
        try:
            sub_ports = self.emu_trunk_subports[trunk_id]
        except KeyError:
            raise neutron_exc.NotFound
        for sub_port_data in sub_ports.copy():
            if sub_port_data["port_id"] == port_id:
                sub_ports.remove(sub_port_data)
                break
        raise neutron_exc.NotFound

    def emu_add_security_group(self, id_: str, name: str) -> None:
        data = get_security_group_data(id_, name)
        self.emu_security_groups.append(data)

    def show_security_group(self, id_: str) -> dict:
        for data in self.emu_security_groups:
            if data["id"] == id_:
                return {"security_group": data}
        raise neutron_exc.NotFound

    def list_security_groups(self, **kwargs) -> dict[str, list[dict]]:
        if not kwargs:
            data_list = self.emu_security_groups
        else:
            data_list = []
            for data in self.emu_security_groups:
                for key, val in kwargs.items():
                    if data[key] == val:
                        data_list.append(data)
                        break
        return {"security_groups": data_list}

    def create_security_group(self, data_dict: dict[str, dict]) -> dict:
        data = data_dict["security_group"]

        data["id"] = f"{data['name']}-id"
        self.emu_security_groups.append(data)

        return data_dict

    def delete_security_group(self, id_: str) -> None:
        data = self.show_security_group(id_)["security_group"]
        self.emu_security_groups.remove(data)

    def create_security_group_rule(self, data_dict: dict[str, dict]) -> None:
        data = data_dict["security_group_rule"]
        self.emu_security_group_rules.append(data)
