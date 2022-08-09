from __future__ import annotations

import time
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.v2_0.client import Client as NeutronClient
from novaclient import exceptions as nova_exc
from novaclient.v2.client import Client as NovaClient
from novaclient.v2.servers import Server as OpenStackInstance

from cloudshell.cp.openstack.exceptions import InstanceNotFound, PortNotFound
from cloudshell.cp.openstack.utils.cached_property import cached_property

if TYPE_CHECKING:
    from cloudshell.cp.openstack.api.api import OsApi
    from cloudshell.cp.openstack.os_api.models import Network, Port


@attr.s(auto_attribs=True, str=False)
class Instance:
    api: ClassVar[OsApi]
    _nova: ClassVar[NovaClient]
    _logger: ClassVar[Logger]

    _os_instance: OpenStackInstance

    def __str__(self) -> str:
        return f"Instance '{self.name}'"

    @classmethod
    def get(cls, id_: str) -> Instance:
        cls._logger.debug(f"Getting an instance with ID '{id_}'")
        try:
            os_instance = cls._nova.servers.get(id_)
        except nova_exc.NotFound:
            raise InstanceNotFound(id_=id_)
        return cls(os_instance)

    @classmethod
    def find_first(cls, name: str) -> Instance:
        cls._logger.debug(f"Searching for first instance with name '{name}'")
        try:
            os_instance = cls._nova.servers.findall(name=name)[0]
        except IndexError:
            raise InstanceNotFound(name=name)
        return cls(os_instance)

    @property
    def id(self) -> str:  # noqa: A003
        return self._os_instance.id

    @property
    def name(self) -> str:
        return self._os_instance.name

    @property
    def interfaces(self) -> Generator[Interface, None, None]:
        self._logger.debug(f"Getting interfaces for the {self}")
        for iface in self._os_instance.interface_list():
            yield self.api.Interface.from_os_interface(self, iface)

    def attach_port(self, port: Port) -> Interface:
        self._logger.debug(f"Attaching the {port} to the {self}")
        for iface in self.interfaces:
            if iface.port_id == port.id:
                self._logger.debug(f"Already attached the {port} to the {self}")
                break
        else:
            os_iface = self._os_instance.interface_attach(
                port_id=port.id, net_id=None, fixed_ip=None
            )
            iface = self.api.Interface.from_os_interface(self, os_iface)
        return iface

    def attach_network(self, network: Network) -> Interface:
        self._logger.debug(f"Attaching a {network} to the {self}")
        os_iface = self._os_instance.interface_attach(
            port_id=None, net_id=network.id, fixed_ip=None
        )
        return self.api.Interface.from_os_interface(self, os_iface)

    def detach_port(self, port: Port) -> None:
        self._logger.debug(f"Detaching the {port} from the {self}")
        self._os_instance.interface_detach(port.id)

    def detach_network(self, network: Network) -> None:
        self._logger.debug(f"Detaching the {network} from the {self}")
        iface = self.find_interface_by_network(network)
        if iface:
            self.detach_port(iface.port)
            if iface.port.name:
                self._wait_port_is_gone(iface.port)
        else:
            self._logger.debug(f"Interface with the {network} not found in the {self}")

    def find_interface_by_network(self, network: Network) -> Interface | None:
        for iface in self.interfaces:
            if iface.network_id == network.id:
                return iface

    def _wait_port_is_gone(self, port: Port):
        for _ in range(5):
            try:
                self.api.Port.get(port.id)
            except PortNotFound:
                break
            else:
                time.sleep(1)


@attr.s(auto_attribs=True)
class Interface:
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    instance: Instance
    port_id: str
    network_id: str
    mac_address: str

    @classmethod
    def from_os_interface(cls, instance: Instance, interface) -> Interface:
        return cls(instance, interface.port_id, interface.net_id, interface.mac_addr)

    @cached_property
    def network(self) -> Network:
        return self.api.Network.get(self.network_id)

    @cached_property
    def port(self) -> Port:
        return self.api.Port.get(self.port_id)