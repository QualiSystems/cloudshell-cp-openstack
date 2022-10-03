from __future__ import annotations

import time
from contextlib import suppress
from logging import Logger
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import PortIsNotGone, PortNotFound
from cloudshell.cp.openstack.os_api.models.network import Network
from cloudshell.cp.openstack.utils.cached_property import cached_property

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi
    from cloudshell.cp.openstack.os_api.models import Subnet, Trunk


def _update_attribute(self: Port, attribute: attr.Attribute, new_value: str) -> str:
    self._neutron.update_port(self.id, {"port": {attribute.name: new_value}})
    return new_value


@attr.s(auto_attribs=True, str=False)
class Port:
    LOCK = Lock()
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str = attr.ib(on_setattr=_update_attribute)  # type: ignore
    network_id: str
    mac_address: str

    def __str__(self) -> str:
        return f"Port '{self.name}'"

    @classmethod
    def from_dict(cls, port_dict: dict) -> Port:
        return cls(
            port_dict["id"],
            port_dict["name"],
            port_dict["network_id"],
            port_dict["mac_address"],
        )

    @classmethod
    def get(cls, id_: str) -> Port:
        cls._logger.debug(f"Getting a port with ID '{id_}'")
        try:
            port_dict = cls._neutron.show_port(id_)["port"]
        except neutron_exc.PortNotFoundClient:
            raise PortNotFound(id_=id_)
        return cls.from_dict(port_dict)

    @classmethod
    def find_first(cls, name: str) -> Port:
        cls._logger.debug(f"Searching for first port with name '{name}'")
        for port_dict in cls._neutron.list_ports(name=name)["ports"]:
            if port_dict["name"] == name:
                break
        else:
            raise PortNotFound(name=name)
        return cls.from_dict(port_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Port, None, None]:  # noqa: A003
        cls._logger.debug("Get all ports")
        for port_dict in cls._neutron.list_ports()["ports"]:
            yield cls.from_dict(port_dict)

    @classmethod
    def create(
        cls,
        name: str,
        network: Network,
        mac_address: str | None = None,
        fixed_ip: str | None = None,
        fixed_ip_subnet: Subnet | None = None,
    ) -> Port:
        assert (fixed_ip and fixed_ip_subnet) or (not fixed_ip and not fixed_ip_subnet)
        port_data = {"name": name, "network_id": network.id, "mac_address": mac_address}
        if fixed_ip and fixed_ip_subnet:
            port_data["fixed_ips"] = [  # type: ignore
                {"subnet_id": fixed_ip_subnet.id, "ip_address": fixed_ip}
            ]
        cls._logger.debug(f"Creating a port with data {port_data}")
        full_port_dict = cls._neutron.create_port({"port": port_data})["port"]
        return cls.from_dict(full_port_dict)

    @classmethod
    def find_or_create(
        cls,
        name: str,
        network: Network,
        mac: str | None = None,
    ) -> Port:
        with cls.LOCK:
            try:
                port = cls.find_first(name)
            except PortNotFound:
                port = cls.create(name, network, mac)
        return port

    @cached_property
    def network(self) -> Network:
        return self.api.Network.get(self.network_id)

    @property
    def trunk(self) -> Trunk | None:
        port_dict = self._neutron.show_port(self.id)["port"]
        trunk_id = port_dict.get("trunk_details", {}).get("trunk_id")
        if trunk_id:
            trunk = self.api.Trunk.get(trunk_id)
        else:
            trunk = None
        return trunk

    def remove(self) -> None:
        self._logger.debug(f"Removing the {self}")
        with suppress(neutron_exc.PortNotFoundClient):
            self._neutron.delete_port(self.id)

    def wait_until_is_gone(self, timeout: int = 5, raise_if_not: bool = True):
        for _ in range(timeout):
            try:
                self.api.Port.get(self.id)
            except PortNotFound:
                break
            else:
                time.sleep(1)
        else:
            if raise_if_not:
                raise PortIsNotGone(self)
