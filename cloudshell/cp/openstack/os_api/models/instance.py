from __future__ import annotations

import time
from enum import Enum
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.v2_0.client import Client as NeutronClient
from novaclient import exceptions as nova_exc
from novaclient.v2.client import Client as NovaClient
from novaclient.v2.servers import Server as OpenStackInstance

from cloudshell.cp.openstack.exceptions import (
    InstanceErrorStateException,
    InstanceNotFound,
    PortIsNotAttached,
)
from cloudshell.cp.openstack.utils.cached_property import cached_property

if TYPE_CHECKING:
    from cloudshell.cp.openstack.api.api import OsApi
    from cloudshell.cp.openstack.os_api.models import Flavor, Image, Network, Port


class InstanceStatus(Enum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    BUILDING = "BUILDING"
    STOPPED = "STOPPED"
    DELETED = "DELETED"
    SHUTOFF = "SHUTOFF"
    OTHER = "_OTHER"

    @classmethod
    def _missing_(cls, value):
        assert isinstance(value, str)
        status = cls.__members__.get(value.upper(), cls.OTHER)
        if status is cls.OTHER:
            status._real_value = value
        return status


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

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Instance, None, None]:  # noqa: A003
        cls._logger.debug("Get all instances")
        for os_instance in cls._nova.servers.list():
            yield cls(os_instance)

    @classmethod
    def create(
        cls,
        name: str,
        image: Image,
        flavor: Flavor,
        network: Network,
        availability_zone: str | None = None,
        affinity_group_id: str | None = None,
        user_data: str | None = None,
    ) -> Instance:
        nics = [{"net-id": network.id}]
        scheduler_hints = {"group": affinity_group_id} if affinity_group_id else None

        os_inst = cls._nova.servers.create(
            name,
            image.id,
            flavor.id,
            nics=nics,
            userdata=user_data,
            availability_zone=availability_zone,
            scheduler_hints=scheduler_hints,
        )
        inst = cls(os_inst)
        inst._wait_for_status(InstanceStatus.ACTIVE)
        return inst

    @property  # noqa: A003
    def id(self) -> str:  # noqa: A003
        return self._os_instance.id

    @property
    def name(self) -> str:
        return self._os_instance.name

    @property
    def status(self) -> InstanceStatus:
        return InstanceStatus(self._os_instance.status)

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
            # os_instance.interface_attach raises an exception
            os_iface = self._nova.servers.interface_attach(
                self._os_instance, port_id=port.id, net_id=None, fixed_ip=None
            )
            iface = self.api.Interface.from_os_interface(self, os_iface)
            self._wait_port_attached(port)
        return iface

    def attach_network(self, network: Network) -> Interface:
        self._logger.debug(f"Attaching a {network} to the {self}")
        # os_instance.interface_attach raises an exception
        os_iface = self._nova.servers.interface_attach(
            self._os_instance, port_id=None, net_id=network.id, fixed_ip=None
        )
        return self.api.Interface.from_os_interface(self, os_iface)

    def detach_port(self, port: Port) -> None:
        self._logger.debug(f"Detaching the {port} from the {self}")
        self._nova.servers.interface_detach(self._os_instance, port.id)

    def detach_network(self, network: Network) -> None:
        self._logger.debug(f"Detaching the {network} from the {self}")
        iface = self.find_interface_by_network(network)
        if iface:
            self.detach_port(iface.port)
            if not iface.port.name:  # probably the port created automatically
                iface.port.wait_until_is_gone(raise_if_not=False)
        else:
            self._logger.debug(f"Interface with the {network} not found in the {self}")

    def find_interface_by_network(self, network: Network) -> Interface | None:
        for iface in self.interfaces:
            if iface.network_id == network.id:
                return iface
        return None

    def power_on(self) -> None:
        if self.status is not InstanceStatus.ACTIVE:
            self._logger.debug(f"Starting the {self}")
            self._os_instance.start()
            self._wait_for_status(InstanceStatus.ACTIVE)
        else:
            self._logger.debug(f"The {self} already active")

    def power_off(self) -> None:
        if self.status is not InstanceStatus.SHUTOFF:
            self._logger.debug(f"Stopping the {self}")
            self._os_instance.stop()
            self._wait_for_status(InstanceStatus.SHUTOFF)
        else:
            self._logger.debug(f"The {self} already stopped")

    def remove(self):
        self._logger.debug(f"Removing {self}")
        self._os_instance.delete()

    def create_snapshot(self, name: str) -> str:
        """Create a snapshot.

        :return: snapshot id
        """
        return self._os_instance.create_image(name)

    def _wait_port_attached(self, port: Port, timeout: int = 5):
        for _ in range(timeout):
            for iface in self.interfaces:
                if iface.port_id == port.id:
                    return
            else:
                time.sleep(1)
        raise PortIsNotAttached(port, self)

    def _wait_for_status(
        self,
        status: InstanceStatus,
        delay: int = 3,
    ) -> None:
        while self.status not in (status, InstanceStatus.ERROR):
            time.sleep(delay)
            self._os_instance.get()
        if self.status is InstanceStatus.ERROR:
            raise InstanceErrorStateException(self._os_instance.fault["message"])


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
