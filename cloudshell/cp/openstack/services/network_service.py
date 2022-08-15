from __future__ import annotations

from ipaddress import IPv4Network, ip_network
from logging import Logger
from threading import Lock

import attr
from neutronclient.common import exceptions as neutron_exc

from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.exceptions import FreeSubnetIsNotFound
from cloudshell.cp.openstack.os_api.models import Network, NetworkType, Subnet
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.cached_property import cached_property


@attr.s(auto_attribs=True)
class QVlanNetwork:
    _api: OsApi
    _resource_conf: OSResourceConfig
    _logger: Logger
    _subnet_lock: Lock = Lock()

    def get_network(self, vlan_id: int) -> Network:
        network = self._api.Network.find_by_vlan_id(vlan_id)
        self._logger.info(f"Using the {network}")
        return network

    def get_or_create_network(self, vlan_id: int, qnq: bool) -> Network:
        try:
            network = self._create_network(vlan_id, qnq)
        except neutron_exc.Conflict:
            self._logger.info(f"Network with VLAN {vlan_id} already created")
            network = self.get_network(vlan_id)
        else:
            self._create_subnet(network)
        return network

    def _create_network(self, vlan_id: int, qnq: bool) -> Network:
        name = self._get_network_name(vlan_id)
        self._logger.info(f"Creating network '{name}' with VLAN {vlan_id}")
        return self._api.Network.create(
            name,
            vlan_id=vlan_id,
            network_type=self._vlan_type,
            qnq=qnq,
            physical_iface_name=self._resource_conf.os_physical_int_name,
        )

    @cached_property
    def _vlan_type(self) -> NetworkType:
        return NetworkType.from_str(self._resource_conf.vlan_type)

    @staticmethod
    def _get_network_name(vlan_id: int) -> str:
        return f"qs_net_segmentation_id_{vlan_id}"

    @staticmethod
    def _get_subnet_name(network_id: str) -> str:
        return f"qs_subnet_{network_id}"

    def _create_subnet(self, network: Network) -> Subnet:
        with self._subnet_lock:
            if not any(network.subnets):
                cidr = self._get_unused_cidr()
                self._logger.info(
                    f"The {network} is missing a subnet, adding a subnet with the "
                    f"CIDR {cidr}"
                )
                name = self._get_subnet_name(network.id)
                subnet = self._api.Subnet.create(
                    name,
                    network,
                    cidr=cidr,
                    ip_version=4,
                    gateway_ip=None,
                )
        return subnet

    def _get_unused_cidr(self) -> str:
        """Gets unused CIDR that excludes the reserved CIDRs.

        We basically start with a 10.0. network to find a subnet that does not overlap
        # with either the reserved_cidrs or currently allocated CIDRs
        # currently supports /24 subnets
        """
        reserved_cidrs = self._resource_conf.os_reserved_networks
        self._logger.info(f"reserved CIDRs: {reserved_cidrs}")

        blacklist_cidrs = self._api.Subnet.get_used_cidrs()
        blacklist_cidrs.update(reserved_cidrs)
        self._logger.info(f"blacklist CIDRs: {blacklist_cidrs}")
        blacklist_subnets = set(map(ip_network, blacklist_cidrs))

        found_subnet = _get_first_free_subnet(blacklist_subnets)
        cidr = str(found_subnet)
        self._logger.info(f"Resolved CIDR: {cidr}")
        return cidr


def _get_first_free_subnet(blacklist_subnets: set[IPv4Network]) -> IPv4Network:
    first_second_octet_dict = {10: range(256), 172: range(16, 32), 192: (168,)}
    for first_octet, second_octets in first_second_octet_dict.items():
        for second_octet in second_octets:
            for third_octet in range(256):
                subnet = IPv4Network(f"{first_octet}.{second_octet}.{third_octet}.0/24")
                if not any(map(subnet.overlaps, blacklist_subnets)):
                    return subnet
    raise FreeSubnetIsNotFound
