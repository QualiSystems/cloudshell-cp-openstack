from __future__ import annotations

from threading import Lock

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import TrunkNotFound
from cloudshell.cp.openstack.os_api.os_api_models.port import Port
from cloudshell.cp.openstack.utils.cached_property import cached_property


@attr.s(auto_attribs=True)
class Trunk:
    LOCK = Lock()
    _neutron: NeutronClient = attr.ib(repr=False)
    id: str  # noqa: A003
    name: str
    port_id: str

    @classmethod
    def from_dict(cls, neutron: NeutronClient, trunk_dict: dict) -> Trunk:
        return cls(
            neutron,
            trunk_dict["id"],
            trunk_dict["name"],
            trunk_dict["port_id"],
        )

    @classmethod
    def get(cls, neutron: NeutronClient, id_: str) -> Trunk:
        try:
            trunk_dict = neutron.show_trunk(id_)["trunk"]
        except neutron_exc.NotFound:
            raise TrunkNotFound(id_=id_)
        return cls.from_dict(neutron, trunk_dict)

    @classmethod
    def find(cls, neutron: NeutronClient, name: str) -> Trunk:
        for trunk_dict in neutron.list_trunks(name=name)["trunks"]:
            if trunk_dict["name"] == name:
                break
        else:
            raise TrunkNotFound(name=name)
        return cls.from_dict(neutron, trunk_dict)

    @classmethod
    def create(cls, neutron: NeutronClient, name: str, port: Port) -> Trunk:
        trunk_data = {"name": name, "port_id": port.id}
        full_trunk_dict = neutron.create_trunk({"trunk": trunk_data})["trunk"]
        return cls.from_dict(neutron, full_trunk_dict)

    @classmethod
    def find_or_create(cls, neutron: NeutronClient, name: str, port: Port) -> Trunk:
        with cls.LOCK:
            try:
                trunk = cls.find(neutron, name)
            except TrunkNotFound:
                trunk = cls.create(neutron, name, port)
        return trunk

    @cached_property
    def port(self) -> Port:
        return Port.get(self._neutron, self.port_id)

    @property
    def sub_ports_ids(self) -> list[str]:
        sub_ports_dicts = self._neutron.trunk_get_subports(self.id)["sub_ports"]
        return [sub_port["port_id"] for sub_port in sub_ports_dicts]

    def remove(self) -> None:
        self._neutron.delete_trunk(self.id)

    def add_sub_port(self, port: Port) -> None:
        sub_port_data = {
            "port_id": port.id,
            "segmentation_id": port.network.segmentation_id,
            "segmentation_type": port.network.network_type.value,
        }

        try:
            self._neutron.trunk_add_subports(self.id, {"sub_ports": [sub_port_data]})
        except neutron_exc.Conflict:
            if port.id not in self.sub_ports_ids:
                pass  # already added, skip
            else:
                raise

    def remove_sub_port(self, port: Port) -> None:
        try:
            self._neutron.trunk_remove_subports(
                self.id, {"sub_ports": [{"port_id": port.id}]}
            )
        except neutron_exc.NotFound:
            pass  # already removed
