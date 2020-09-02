from cloudshell.cp.core.request_actions.models import DeployedApp
from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
)

from cloudshell.cp.openstack import constants


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class OSNovaImgDeployedApp(DeployedApp):
    DEPLOYMENT_PATH = constants.OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH

    availability_zone = ResourceAttrRODeploymentPath("Availability Zone")
    image_id = ResourceAttrRODeploymentPath("Image ID")
    instance_flavor = ResourceAttrRODeploymentPath("Instance Flavor")
    add_floating_ip = ResourceBoolAttrRODeploymentPath("Add Floating IP")
    affinity_group_id = ResourceAttrRODeploymentPath("Affinity Group ID")
    floating_ip_subnet_id = ResourceAttrRODeploymentPath("Floating IP Subnet ID")
    auto_udev = ResourceBoolAttrRODeploymentPath("Auto udev")
