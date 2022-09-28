from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from novaclient import exceptions as nova_exc
from novaclient.v2.client import Client as NovaClient
from novaclient.v2.flavors import Flavor as OpenStackFlavor

from cloudshell.cp.openstack.exceptions import FlavorNotFound

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi


@attr.s(auto_attribs=True, str=False)
class Flavor:
    api: ClassVar[OsApi]
    _nova: ClassVar[NovaClient]
    _logger: ClassVar[Logger]

    _os_flavor: OpenStackFlavor

    def __str__(self) -> str:
        return f"Flavor '{self.name}'"

    @classmethod
    def get(cls, id_: str) -> Flavor:
        cls._logger.debug(f"Getting a flavor with ID '{id_}'")
        try:
            os_flavor = cls._nova.flavors.get(id_)
        except nova_exc.NotFound:
            raise FlavorNotFound(id_=id_)
        return cls(os_flavor)

    @classmethod
    def find_first(cls, name: str) -> Flavor:
        cls._logger.debug(f"Searching for the first flavor with name '{name}'")
        try:
            os_flavor = cls._nova.flavors.findall(name=name)[0]
        except IndexError:
            raise FlavorNotFound(name=name)
        return cls(os_flavor)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Flavor, None, None]:  # noqa: A003
        cls._logger.debug("Get all flavors")
        for os_flavor in cls._nova.flavors.list():
            yield cls(os_flavor)

    @property  # noqa: A003
    def id(self) -> str:  # noqa: A003
        return self._os_flavor.id

    @property
    def name(self) -> str:
        return self._os_flavor.name

    @property
    def vcpus(self) -> int:
        return self._os_flavor.vcpus

    @property
    def ram_mb(self) -> int:
        # OpenStack returns RAM in MB
        return self._os_flavor.ram

    @property
    def disk_gb(self) -> int:
        # OpenStack returns disk in GB
        return self._os_flavor.disk
