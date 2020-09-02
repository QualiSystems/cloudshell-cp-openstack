from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.instance_helpers import (
    get_floating_ip,
    get_private_ip,
)


def refresh_ip(
    api: OSApi,
    deployed_app: OSNovaImgDeployedApp,
    resource_conf: OSResourceConfig,
):
    instance = api.get_instance(deployed_app.vmdetails.uid)

    private_net_name = api.get_network_name(resource_conf.os_mgmt_net_id)
    new_private_ip = get_private_ip(instance, private_net_name)

    new_public_ip = get_floating_ip(instance)

    if new_private_ip != deployed_app.private_ip:
        deployed_app.update_private_ip(deployed_app.name, new_private_ip)
    if new_public_ip != deployed_app.public_ip:
        deployed_app.update_public_ip(new_public_ip)
