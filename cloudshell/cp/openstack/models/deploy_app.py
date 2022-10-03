from __future__ import annotations

from dataclasses import dataclass

from cloudshell.cp.core.request_actions.models import DeployApp
from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
    ResourceListAttrRO,
)

from cloudshell.cp.openstack import constants
from cloudshell.cp.openstack.models.attr_names import ResourceAttrName
from cloudshell.cp.openstack.utils.models_helper import get_port_range, is_cidr


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name: str, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name: str, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


@dataclass
class SecurityGroupRule:
    DEFAULT_CIDR = "0.0.0.0/0"
    DEFAULT_PROTOCOL = "tcp"
    port_range_min: int
    port_range_max: int
    cidr: str = DEFAULT_CIDR
    protocol: str = DEFAULT_PROTOCOL

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
            protocol = parts[1].lower()
        elif len(parts) == 2:
            if is_cidr(parts[0]):
                cidr = parts[0]
            else:
                protocol = parts[0].lower()

        if cidr is not None and not is_cidr(cidr):
            raise ValueError(emsg)

        return cls(
            min_,
            max_,
            cidr or cls.DEFAULT_CIDR,
            protocol or cls.DEFAULT_PROTOCOL,
        )


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
    user_data = ResourceAttrRODeploymentPath(ATTR_NAME.user_data)
    inbound_ports = ResourceInboundPortsRO(ATTR_NAME.inbound_ports)
    behavior_during_save = ResourceAttrRODeploymentPath(ATTR_NAME.behavior_during_save)
    private_ip = ResourceAttrRODeploymentPath(ATTR_NAME.private_ip)
