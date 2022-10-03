from cloudshell.cp.core.request_actions.models import DeployedApp
from cloudshell.shell.standards.core.resource_config_entities import (
    ResourceAttrRO,
    ResourceBoolAttrRO,
)

from cloudshell.cp.openstack import constants
from cloudshell.cp.openstack.models.attr_names import ResourceAttrName


class ResourceAttrRODeploymentPath(ResourceAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH"):
        super().__init__(name, namespace)


class ResourceBoolAttrRODeploymentPath(ResourceBoolAttrRO):
    def __init__(self, name, namespace="DEPLOYMENT_PATH", *args, **kwargs):
        super().__init__(name, namespace, *args, **kwargs)


class OSNovaImgDeployedApp(DeployedApp):
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
    private_ip = ResourceAttrRODeploymentPath(ATTR_NAME.private_ip)
