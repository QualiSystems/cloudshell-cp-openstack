from __future__ import annotations

from contextlib import suppress
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import FloatingIpNotFound

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi
    from cloudshell.cp.openstack.os_api.models import Port, Subnet


@attr.s(auto_attribs=True, str=False)
class FloatingIp:
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    ip_address: str

    def __str__(self) -> str:
        return f"Floating IP '{self.ip_address}'"

    @classmethod
    def from_dict(cls, data_dict: dict) -> FloatingIp:
        return cls(data_dict["id"], data_dict["floating_ip_address"])

    @classmethod
    def get(cls, id_: str) -> FloatingIp:
        cls._logger.debug(f"Getting a floating IP with ID '{id_}'")
        try:
            data_dict = cls._neutron.show_floatingip(id_)["floatingip"]
        except neutron_exc.NotFound:
            raise FloatingIpNotFound(id_=id_)
        return cls.from_dict(data_dict)

    @classmethod
    def find_by_ip(cls, ip: str) -> FloatingIp:
        cls._logger.debug(f"Finding a floating IP with IP '{ip}'")
        try:
            data_dict = cls._neutron.list_floatingips(floating_ip_address=ip)[
                "floatingips"
            ][0]
        except IndexError:
            raise FloatingIpNotFound(ip=ip)
        return cls.from_dict(data_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[FloatingIp, None, None]:  # noqa: A003
        cls._logger.debug("Get all floating IPs")
        for data_dict in cls._neutron.list_floatingips()["floatingips"]:
            yield cls.from_dict(data_dict)

    @classmethod
    def create(
        cls,
        floating_subnet: Subnet,
        port: Port,
    ) -> FloatingIp:
        floating_ip_data = {
            "floating_network_id": floating_subnet.network_id,
            "subnet_id": floating_subnet.id,
            "port_id": port.id,
        }
        cls._logger.debug(f"Creating a floating IP with data {floating_ip_data}")
        full_data_dict = cls._neutron.create_floatingip(
            {"floatingip": floating_ip_data}
        )["floatingip"]
        return cls.from_dict(full_data_dict)

    def remove(self) -> None:
        self._logger.debug(f"Removing the {self}")
        with suppress(neutron_exc.NotFound):
            self._neutron.delete_floatingip(self.id)
