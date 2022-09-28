from __future__ import annotations

from enum import Enum
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import NetworkInUse, NetworkNotFound
from cloudshell.cp.openstack.os_api.models.subnet import Subnet

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi


class NetworkType(Enum):
    LOCAL = "local"
    FLAT = "flat"
    VLAN = "vlan"
    VXLAN = "vxlan"
    GRE = "gre"
    GENEVE = "geneve"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            return cls(value.lower())


@attr.s(auto_attribs=True, str=False)
class Network:
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str
    network_type: NetworkType
    vlan_id: int | None
    is_external: bool

    def __str__(self) -> str:
        return f"Network '{self.name}'"

    @classmethod
    def from_dict(cls, net_dict: dict) -> Network:
        return cls(
            net_dict["id"],
            net_dict["name"],
            network_type=NetworkType(net_dict["provider:network_type"]),
            vlan_id=net_dict["provider:segmentation_id"],
            is_external=net_dict["router:external"],
        )

    @classmethod
    def get(cls, id_: str) -> Network:
        cls._logger.debug(f"Getting a network with ID '{id_}'")
        try:
            net_dict = cls._neutron.show_network(id_)["network"]
        except neutron_exc.NetworkNotFoundClient:
            raise NetworkNotFound(id_=id_)
        return cls.from_dict(net_dict)

    @classmethod
    def find_first(cls, name: str) -> Network:
        cls._logger.debug(f"Searching for first network with name '{name}'")
        for net_dict in cls._neutron.list_networks(name=name)["networks"]:
            if net_dict["name"] == name:
                break
        else:
            raise NetworkNotFound(name=name)
        return cls.from_dict(net_dict)

    @classmethod
    def find_by_vlan_id(cls, vlan_id: int) -> Network:
        # Openstack can have only one network with specific VLAN
        networks = cls._neutron.list_networks(**{"provider:segmentation_id": vlan_id})
        try:
            net_dict = networks["networks"][0]
        except IndexError:
            raise NetworkNotFound(vlan_id=vlan_id) from None
        return cls.from_dict(net_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Network, None, None]:  # noqa: A003
        cls._logger.debug("Get all networks")
        for net_dict in cls._neutron.list_networks()["networks"]:
            yield cls.from_dict(net_dict)

    @classmethod
    def create(
        cls,
        name: str,
        *,
        vlan_id: int | None = None,
        network_type: NetworkType | None = None,
        qnq: bool = False,
        physical_iface_name: str | None = None,
    ) -> Network:
        data = {"name": name, "admin_state_up": True}
        if network_type:
            data["provider:network_type"] = network_type.value
        if vlan_id:
            data["provider:segmentation_id"] = vlan_id
            if qnq:
                data["vlan_transparent"] = True
            if network_type is NetworkType.VLAN:
                data["provider:physical_network"] = physical_iface_name
        cls._logger.debug(f"Creating a network with params: {data}")
        net_dict = cls._neutron.create_network({"network": data})["network"]
        return cls.from_dict(net_dict)

    @property
    def subnets(self) -> Generator[Subnet, None, None]:
        yield from self.api.Subnet.find_by_network(self.id)

    def remove(self, raise_in_use: bool = True) -> None:
        self._logger.debug(f"Removing {self}")
        try:
            self._neutron.delete_network(self.id)
        except neutron_exc.NetworkNotFoundClient:
            pass  # network already removed
        except neutron_exc.NetworkInUseClient:
            if raise_in_use:
                raise NetworkInUse(self)
