from __future__ import annotations

from contextlib import suppress
from logging import Logger
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import TrunkNotFound
from cloudshell.cp.openstack.utils.cached_property import cached_property

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi
    from cloudshell.cp.openstack.os_api.models.port import Port


@attr.s(auto_attribs=True, str=False)
class Trunk:
    LOCK = Lock()
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str
    port_id: str

    def __str__(self) -> str:
        return f"Trunk '{self.name}'"

    @classmethod
    def from_dict(cls, trunk_dict: dict) -> Trunk:
        return cls(
            trunk_dict["id"],
            trunk_dict["name"],
            trunk_dict["port_id"],
        )

    @classmethod
    def get(cls, id_: str) -> Trunk:
        cls._logger.debug(f"Getting a trunk with ID '{id_}'")
        try:
            trunk_dict = cls._neutron.show_trunk(id_)["trunk"]
        except neutron_exc.NotFound:
            raise TrunkNotFound(id_=id_)
        return cls.from_dict(trunk_dict)

    @classmethod
    def find_first(cls, name: str) -> Trunk:
        cls._logger.debug(f"Searching for first trunk with name '{name}'")
        for trunk_dict in cls._neutron.list_trunks(name=name)["trunks"]:
            if trunk_dict["name"] == name:
                break
        else:
            raise TrunkNotFound(name=name)
        return cls.from_dict(trunk_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Trunk, None, None]:  # noqa: A003
        cls._logger.debug("Get all trunks")
        for trunk_dict in cls._neutron.list_trunks()["trunks"]:
            yield cls.from_dict(trunk_dict)

    @classmethod
    def create(cls, name: str, port: Port) -> Trunk:
        trunk_data = {"name": name, "port_id": port.id}
        cls._logger.debug(f"Creating a trunk with data {trunk_data}")
        full_trunk_dict = cls._neutron.create_trunk({"trunk": trunk_data})["trunk"]
        return cls.from_dict(full_trunk_dict)

    @classmethod
    def find_or_create(cls, name: str, port: Port) -> Trunk:
        with cls.LOCK:
            try:
                trunk = cls.find_first(name)
            except TrunkNotFound:
                trunk = cls.create(name, port)
        return trunk

    @cached_property
    def port(self) -> Port:
        return self.api.Port.get(self.port_id)

    @property
    def sub_ports_ids(self) -> list[str]:
        try:
            sub_ports_dicts = self._neutron.trunk_get_subports(self.id)["sub_ports"]
        except neutron_exc.NotFound:
            raise TrunkNotFound(id_=self.id)

        self._logger.debug(f"Got sub ports {sub_ports_dicts} for the {self}")
        return [sub_port["port_id"] for sub_port in sub_ports_dicts]

    @property
    def sub_ports(self) -> Generator[Port, None, None]:
        for sub_port_id in self.sub_ports_ids:
            yield self.api.Port.get(sub_port_id)

    def remove(self) -> None:
        self._logger.debug(f"Removing the {self}")
        with suppress(neutron_exc.NotFound):
            self._neutron.delete_trunk(self.id)

    def add_sub_port(self, port: Port) -> None:
        sub_port_data = {
            "port_id": port.id,
            "segmentation_id": port.network.vlan_id,
            "segmentation_type": "vlan",
        }

        try:
            self._logger.debug(f"Adding sub port {sub_port_data} to the {self}")
            self._neutron.trunk_add_subports(self.id, {"sub_ports": [sub_port_data]})
        except neutron_exc.Conflict:
            if port.id in self.sub_ports_ids:
                self._logger.debug(f"Sub {port} already added to the {self}")
            else:
                raise

    def remove_sub_port(self, port: Port) -> None:
        self._logger.debug(f"Removing the Sub {port} from the {self}")
        try:
            self._neutron.trunk_remove_subports(
                self.id, {"sub_ports": [{"port_id": port.id}]}
            )
        except neutron_exc.NotFound:
            self._logger.debug(f"Sub port {port} already removed from the {self}")
