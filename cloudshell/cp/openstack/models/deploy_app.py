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


class ResourceAttrName:
    availability_zone = "Availability Zone"
    image_id = "Image ID"
    instance_flavor = "Instance Flavor"
    add_floating_ip = "Add Floating IP"
    affinity_group_id = "Affinity Group ID"
    floating_ip_subnet_id = "Floating IP Subnet ID"
    auto_udev = "Auto udev"
    inbound_ports = "Inbound Ports"
    behavior_during_save = "Behavior during save"


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
    def from_str(cls, string: str) -> SecurityGroupRule:
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
    ATTR_NAME = ResourceAttrName

    availability_zone = ResourceAttrRODeploymentPath(ATTR_NAME.availability_zone)
    image_id = ResourceAttrRODeploymentPath(ATTR_NAME.image_id)
    instance_flavor = ResourceAttrRODeploymentPath(ATTR_NAME.instance_flavor)
    add_floating_ip = ResourceBoolAttrRODeploymentPath(ATTR_NAME.add_floating_ip)
    affinity_group_id = ResourceAttrRODeploymentPath(ATTR_NAME.affinity_group_id)
    floating_ip_subnet_id = ResourceAttrRODeploymentPath(
        ATTR_NAME.floating_ip_subnet_id
    )
    auto_udev = ResourceBoolAttrRODeploymentPath(ATTR_NAME.auto_udev)
    inbound_ports = ResourceInboundPortsRO(ATTR_NAME.inbound_ports)
    behavior_during_save = ResourceAttrRODeploymentPath(ATTR_NAME.behavior_during_save)
