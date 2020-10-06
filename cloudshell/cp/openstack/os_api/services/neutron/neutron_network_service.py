import time
from ipaddress import IPv4Network, ip_network
from logging import Logger
from typing import List, Set

from neutronclient.v2_0.client import Client as NeutronClient
from neutronclient.v2_0.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.exceptions import (
    FreeSubnetIsNotFoundException,
    NetworkException,
    NetworkNotFoundException,
    SubnetNotFoundException,
)
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class NeutronService:
    def __init__(self, neutron: NeutronClient, logger: Logger):
        self._neutron = neutron
        self._logger = logger

    def get_network(self, **kwargs) -> dict:
        nets = self._neutron.list_networks(**kwargs)["networks"]
        if not nets:
            raise NetworkNotFoundException(f"Network with kwargs {kwargs} not found.")
        elif len(nets) > 1:
            raise NetworkException(f"Found more than one network with kwargs {kwargs}")
        return nets[0]

    def _get_subnets(self, **kwargs) -> List[dict]:
        subnets = self._neutron.list_subnets(**kwargs)["subnets"]
        if not subnets:
            raise SubnetNotFoundException(f"Subnet with kwargs {kwargs} not found")
        return subnets

    def get_subnet(self, **kwargs) -> dict:
        subnets = self._get_subnets(**kwargs)
        if len(subnets) > 1:
            raise NetworkException(f"Found more than one subnet with kwargs {kwargs}")
        return subnets[0]

    def get_network_name(self, net_id: str) -> str:
        return self.get_network(id=net_id)["name"]

    def create_network(self, net_data: dict) -> dict:
        return self._neutron.create_network(net_data)

    def remove_network(self, net_id: str):
        self._logger.info(f"Removing network {net_id}")
        ports = self._neutron.list_ports(network_id=net_id)["ports"]
        retries = 3
        while len(ports) > 1 and retries:
            time.sleep(1)
            ports = self._neutron.list_ports(network_id=net_id)["ports"]
            retries -= 1

        try:
            subnets = self._get_subnets(network_id=net_id)
        except SubnetNotFoundException:
            subnets = []

        for subnet_dict in subnets:
            try:
                self._neutron.delete_subnet(subnet_dict["id"])
            except neutron_exceptions.Conflict:
                pass
        try:
            self._neutron.delete_network(net_id)
        except (
            neutron_exceptions.NetworkInUseClient,
            neutron_exceptions.NetworkNotFoundClient,
        ):
            pass

    def get_or_create_net_with_segmentation_id(
        self, segmentation_id: int, resource_conf: OSResourceConfig, net_prefix: str
    ) -> dict:
        try:
            net = self._create_net_with_segmentation_id(
                segmentation_id, resource_conf, net_prefix
            )
        except neutron_exceptions.Conflict:
            net = self.get_net_with_segmentation(segmentation_id)
        return net

    def _create_net_with_segmentation_id(
        self, segmentation_id: int, resource_conf: OSResourceConfig, net_prefix: str
    ) -> dict:
        data = {
            "provider:network_type": resource_conf.vlan_type.lower(),
            "provider:segmentation_id": segmentation_id,
            "name": f"{net_prefix}_{segmentation_id}",
            "admin_state_up": True,
        }
        if resource_conf.vlan_type.lower() == "vlan":
            data["provider:physical_network"] = resource_conf.os_physical_int_name
        return self._neutron.create_network({"network": data})["network"]

    def get_net_with_segmentation(self, segmentation_id: int) -> dict:
        net_dict = self._neutron.list_networks(
            **{"provider:segmentation_id": segmentation_id}
        )
        try:
            net = net_dict["networks"][0]
        except IndexError:
            emsg = f"Network with {segmentation_id} segmentation id not found"
            raise NetworkNotFoundException(emsg)
        return net

    def create_subnet(self, net_id: str, reserved_networks: List[str]):
        cidr = self._get_unused_cidr(reserved_networks)
        data = {
            "subnet": {
                "cidr": cidr,
                "network_id": net_id,
                "ip_version": 4,
                "name": f"qs_subnet_{net_id}",
                "gateway_ip": None,
            }
        }
        self._logger.info(f"Calling neutron client create_subnet with request {data}")
        new_subnet = self._neutron.create_subnet(data)["subnet"]
        self._logger.info(f"Created new subnet: {new_subnet}")
        return new_subnet

    def _get_unused_cidr(self, reserved_cidrs: List[str]) -> str:
        """Gets unused CIDR that excludes the reserved CIDRs.

        We basically start with a 10.0. network to find a subnet that does not overlap
        # with either the reserved_cidrs or currently allocated CIDRs
        # currently supports /24 subnets
        """
        self._logger.info(f"reserved CIDRs: {reserved_cidrs}")

        current_subnets = self._neutron.list_subnets(fields=["cidr", "id"])["subnets"]
        blacklist_cidrs = {subnet["cidr"] for subnet in current_subnets}
        blacklist_cidrs.update(reserved_cidrs)
        self._logger.info(f"blacklist CIDRs: {blacklist_cidrs}")
        blacklist_subnets = set(map(ip_network, blacklist_cidrs))

        found_subnet = _generate_subnet(blacklist_subnets)
        cidr = str(found_subnet)
        self._logger.info(f"Resolved CIDR: {cidr}")
        return cidr

    def create_floating_ip(self, subnet_id: str, port_id: str) -> str:
        subnet_dict = self.get_subnet(id=subnet_id)
        floating_ip_create_dict = {
            "floatingip": {
                "floating_network_id": subnet_dict["network_id"],
                "subnet_id": subnet_id,
                "port_id": port_id,
            }
        }
        floating_ip_dict = self._neutron.create_floatingip(floating_ip_create_dict)
        try:
            ip = floating_ip_dict["floatingip"]["floating_ip_address"]
        except KeyError:
            emsg = f"Unable to assign Floating IP on Subnet {subnet_id}"
            raise NetworkException(emsg)
        return ip

    def delete_floating_ip(self, ip: str):
        floating_ips_dict = self._neutron.list_floatingips(floating_ip_address=ip)
        floating_ip_id = floating_ips_dict["floatingips"][0]["id"]
        self._neutron.delete_floatingip(floating_ip_id)

    def create_security_group(self, sg_name: str) -> str:
        resp = self._neutron.create_security_group(
            {"security_group": {"name": sg_name}}
        )
        return resp["security_group"]["id"]

    def create_security_group_rule(
        self, sg_id: str, cidr: str, port_min: int, port_max: int, protocol: str
    ):
        self._neutron.create_security_group_rule(
            {
                "security_group_rule": {
                    "remote_ip_prefix": cidr,
                    "port_range_min": port_min,
                    "port_range_max": port_max,
                    "protocol": protocol,
                    "security_group_id": sg_id,
                    "direction": "ingress",
                }
            }
        )

    def delete_security_group(self, sg_id: str):
        self._neutron.delete_security_group(sg_id)


def _generate_subnet(blacklist_subnets: Set[IPv4Network]) -> IPv4Network:
    first_second_octet_dict = {10: range(256), 172: range(16, 32), 192: (168,)}
    for first_octet, second_octets in first_second_octet_dict.items():
        for second_octet in second_octets:
            for third_octet in range(256):
                subnet = IPv4Network(f"{first_octet}.{second_octet}.{third_octet}.0/24")
                if not any(map(subnet.overlaps, blacklist_subnets)):
                    return subnet
    raise FreeSubnetIsNotFoundException("All Subnets Exhausted")
