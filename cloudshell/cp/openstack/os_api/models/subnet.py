from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING, ClassVar, Generator

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import SubnetNotFound
from cloudshell.cp.openstack.utils.cached_property import cached_property

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.api import OsApi
    from cloudshell.cp.openstack.os_api.models import Network


@attr.s(auto_attribs=True, str=False)
class Subnet:
    api: ClassVar[OsApi]
    _neutron: ClassVar[NeutronClient]
    _logger: ClassVar[Logger]

    id: str  # noqa: A003
    name: str
    network_id: str
    ip_version: int
    cidr: str
    gateway: str
    allocation_pools: list[tuple[str, str]]

    def __str__(self) -> str:
        return f"Subnet '{self.name}'"

    @classmethod
    def from_dict(cls, subnet_dict: dict) -> Subnet:
        allocation_pools = [
            (pool["start"], pool["end"]) for pool in subnet_dict["allocation_pools"]
        ]
        return cls(
            subnet_dict["id"],
            subnet_dict["name"],
            network_id=subnet_dict["network_id"],
            ip_version=subnet_dict["ip_version"],
            cidr=subnet_dict["cidr"],
            gateway=subnet_dict["gateway_ip"],
            allocation_pools=allocation_pools,
        )

    @classmethod
    def get(cls, id_: str) -> Subnet:
        cls._logger.debug(f"Getting a subnet with ID '{id_}'")
        try:
            subnet_dict = cls._neutron.show_subnet(id_)["subnet"]
        except neutron_exc.NotFound:
            raise SubnetNotFound(id_=id_)
        return cls.from_dict(subnet_dict)

    @classmethod
    def find_by_network(cls, network_id: str) -> Generator[Subnet, None, None]:
        for subnet_dict in cls._neutron.list_subnets(network_id=network_id)["subnets"]:
            yield cls.from_dict(subnet_dict)

    @classmethod  # noqa: A003
    def all(cls) -> Generator[Subnet, None, None]:  # noqa: A003
        cls._logger.debug("Get all subnets")
        for subnet_dict in cls._neutron.list_subnets()["subnets"]:
            yield cls.from_dict(subnet_dict)

    @classmethod
    def create(
        cls,
        name: str,
        network: Network,
        cidr: str,
        ip_version: int = 4,
        gateway_ip: str | None = None,
        allocation_pools: list[tuple[str, str]] | None = None,
    ) -> Subnet:
        ip_pools = [
            {"start": pool[0], "end": pool[1]} for pool in allocation_pools or []
        ]
        data = {
            "name": name,
            "network_id": network.id,
            "cidr": cidr,
            "ip_version": ip_version,
            "gateway_ip": gateway_ip,
            "allocation_pools": ip_pools,
        }
        cls._logger.debug(f"Creating a subnet with params: {data}")
        subnet_dict = cls._neutron.create_subnet({"subnet": data})["subnet"]
        return cls.from_dict(subnet_dict)

    @classmethod
    def get_used_cidrs(cls) -> set[str]:
        subnets = cls._neutron.list_subnets(fields=["cidr"])["subnets"]
        cidrs = {s["cidr"] for s in subnets}
        cls._logger.debug(f"Looking for used CIDRs - {cidrs}")
        return cidrs

    @cached_property
    def network(self) -> Network:
        return self.api.Network.get(self.network_id)
