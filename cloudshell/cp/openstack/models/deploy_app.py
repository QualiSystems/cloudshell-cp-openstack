from __future__ import annotations

from dataclasses import dataclass

from cloudshell.cp.core.request_actions.models import DeployApp
from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
    ResourceListAttrRO,
)

from cloudshell.cp.openstack import constants
from cloudshell.cp.openstack.utils.models_helper import get_port_range, is_cidr


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name: str, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name: str, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


@dataclass
class SecurityGroupRule:
    port_range_min: int
    port_range_max: int
    cidr: str = "0.0.0.0/0"
    protocol: str = "tcp"

    @classmethod
    def from_str(cls, string: str) -> "SecurityGroupRule":
        emsg = (
            f'Security group rule is not supported format: "{string}".\n'
            f"Should be [cidr:][protocol:]port-or-port-range"
        )
        parts = string.strip().split(":")
        try:
            min_, max_ = get_port_range(parts[-1])
        except ValueError:
            raise ValueError(emsg)

        cidr = protocol = None
        if len(parts) == 3:
            cidr = parts[0]
            protocol = parts[1]
        elif len(parts) == 2:
            if is_cidr(parts[0]):
                cidr = parts[0]
            else:
                protocol = parts[0]

        if cidr is not None and not is_cidr(cidr):
            raise ValueError(emsg)

        kwargs = {"port_range_min": min_, "port_range_max": max_}
        if protocol:
            kwargs["protocol"] = protocol.lower()
        if cidr:
            kwargs["cidr"] = cidr
        return cls(**kwargs)


class ResourceInboundPortsRO(ResourceListAttrRO):
    def __init__(self, name: str, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)

    def __get__(self, instance, owner) -> list[SecurityGroupRule]:
        val = super().__get__(instance, owner)
        if not isinstance(val, list):
            return val
        return list(map(SecurityGroupRule.from_str, val))


class OSNovaImgDeployApp(DeployApp):
    DEPLOYMENT_PATH = constants.OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH

    availability_zone = ResourceAttrRODeploymentPath("Availability Zone")
    image_id = ResourceAttrRODeploymentPath("Image ID")
    instance_flavor = ResourceAttrRODeploymentPath("Instance Flavor")
    add_floating_ip = ResourceBoolAttrRODeploymentPath("Add Floating IP")
    affinity_group_id = ResourceAttrRODeploymentPath("Affinity Group ID")
    floating_ip_subnet_id = ResourceAttrRODeploymentPath("Floating IP Subnet ID")
    auto_udev = ResourceBoolAttrRODeploymentPath("Auto udev")
    inbound_ports = ResourceInboundPortsRO("Inbound Ports")
