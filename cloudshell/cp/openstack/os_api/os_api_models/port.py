from __future__ import annotations

from threading import Lock

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import PortNotFound
from cloudshell.cp.openstack.os_api.os_api_models.network import Network
from cloudshell.cp.openstack.utils.cached_property import cached_property


@attr.s(auto_attribs=True)
class Port:
    LOCK = Lock()
    _neutron: NeutronClient = attr.ib(repr=False)
    id: str  # noqa: A003
    name: str
    network_id: str
    mac_address: str

    @classmethod
    def from_dict(cls, neutron: NeutronClient, port_dict: dict) -> Port:
        return cls(
            neutron,
            port_dict["id"],
            port_dict["name"],
            port_dict["network_id"],
            port_dict["mac_address"],
        )

    @classmethod
    def get(cls, neutron: NeutronClient, id_: str) -> Port:
        try:
            port_dict = neutron.show_port(id_)["port"]
        except neutron_exc.PortNotFoundClient:
            raise PortNotFound(id_=id_)
        return cls.from_dict(neutron, port_dict)

    @classmethod
    def find(cls, neutron: NeutronClient, name: str) -> Port:
        for port_dict in neutron.list_ports(name=name)["ports"]:
            if port_dict["name"] == name:
                break
        else:
            raise PortNotFound(name=name)
        return cls.from_dict(neutron, port_dict)

    @classmethod
    def create(
        cls,
        neutron: NeutronClient,
        name: str,
        network: Network,
        mac_address: str | None = None,
    ) -> Port:
        port_data = {"name": name, "network_id": network.id, "mac_address": mac_address}
        full_port_dict = neutron.create_port({"port": port_data})["port"]
        return cls.from_dict(neutron, full_port_dict)

    @classmethod
    def find_or_create(
        cls,
        neutron: NeutronClient,
        name: str,
        network: Network,
        mac: str | None = None,
    ) -> Port:
        with cls.LOCK:
            try:
                port = cls.find(neutron, name)
            except PortNotFound:
                port = cls.create(neutron, name, network, mac)
        return port

    @cached_property
    def network(self) -> Network:
        return Network.get(self._neutron, self.network_id)

    def remove(self) -> None:
        self._neutron.delete_port(self.id)
