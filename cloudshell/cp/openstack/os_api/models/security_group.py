from __future__ import annotations

from contextlib import suppress
from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import SecurityGroupNotFound

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi


@attr.s(auto_attribs=True, str=False)
class SecurityGroup:
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str

    def __str__(self) -> str:
        return f"Security Group '{self.name}'"

    @classmethod
    def from_dict(cls, data_dict: dict) -> SecurityGroup:
        return cls(data_dict["id"], data_dict["name"])

    @classmethod
    def get(cls, id_: str) -> SecurityGroup:
        cls._logger.debug(f"Getting a Security Group with ID '{id_}'")
        try:
            data_dict = cls._neutron.show_security_group(id_)["security_group"]
        except neutron_exc.NotFound:
            raise SecurityGroupNotFound(id_=id_)
        return cls.from_dict(data_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[SecurityGroup, None, None]:  # noqa: A003
        cls._logger.debug("Get all Security Groups")
        for data_dict in cls._neutron.list_security_groups()["security_groups"]:
            yield cls.from_dict(data_dict)

    @classmethod
    def create(cls, name: str) -> SecurityGroup:
        cls._logger.debug(f"Creating a Security Group with name {name}")
        full_data = cls._neutron.create_security_group(
            {"security_group": {"name": name}}
        )["security_group"]
        return cls.from_dict(full_data)

    def add_rule(
        self,
        cidr: str,
        protocol: str,
        port_range_min: int,
        port_range_max: int,
        direction: str,
    ) -> None:
        data = {
            "remote_ip_prefix": cidr,
            "port_range_min": port_range_min,
            "port_range_max": port_range_max,
            "protocol": protocol,
            "security_group_id": self.id,
            "direction": direction,
        }
        self._neutron.create_security_group_rule({"security_group_rule": data})

    def remove(self) -> None:
        self._logger.debug(f"Removing the {self}")
        with suppress(neutron_exc.NotFound):
            self._neutron.delete_security_group(self.id)
