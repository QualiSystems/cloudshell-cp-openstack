from __future__ import annotations

import time
from logging import Logger

from neutronclient.v2_0.client import Client as NeutronClient
from neutronclient.v2_0.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.exceptions import (
    NetworkException,
    NetworkNotFoundException,
    SubnetNotFoundException,
)


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

    def _get_subnets(self, **kwargs) -> list[dict]:
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
