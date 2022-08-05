from __future__ import annotations

from enum import Enum

import attr
from neutronclient.common import exceptions as neutron_exc
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.openstack.exceptions import NetworkNotFound


class NetworkType(Enum):
    local = "local"
    flat = "flat"
    vlan = "vlan"
    vxlan = "vxlan"
    gre = "gre"


@attr.s(auto_attribs=True)
class Network:
    _neutron: NeutronClient = attr.ib(repr=False)
    id: str  # noqa: A003
    name: str
    network_type: NetworkType
    segmentation_id: int | None

    @classmethod
    def from_dict(cls, neutron: NeutronClient, net_dict: dict) -> Network:
        return cls(
            neutron,
            net_dict["id"],
            net_dict["name"],
            network_type=NetworkType(net_dict["provider:network_type"]),
            segmentation_id=net_dict["provider:segmentation_id"],
        )

    @classmethod
    def get(cls, neutron: NeutronClient, id_: str) -> Network:
        try:
            net_dict = neutron.show_network(id_)["network"]
        except neutron_exc.NetworkNotFoundClient:
            raise NetworkNotFound(id_=id_)
        return cls.from_dict(neutron, net_dict)

    @classmethod
    def find(cls, neutron: NeutronClient, name: str) -> Network:
        for net_dict in neutron.list_networks(name=name)["networks"]:
            if net_dict["name"] == name:
                break
        else:
            raise NetworkNotFound(name=name)
        return cls.from_dict(neutron, net_dict)
