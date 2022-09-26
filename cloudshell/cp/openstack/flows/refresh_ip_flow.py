from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.resource_config import OSResourceConfig


def refresh_ip(
    api: OsApi,
    deployed_app: OSNovaImgDeployedApp,
    resource_conf: OSResourceConfig,
):
    instance = api.Instance.get(deployed_app.vmdetails.uid)
    mgmt_iface = instance.find_interface_by_port_name("mgmt")

    new_private_ip = mgmt_iface.fixed_ip
    new_public_ip = mgmt_iface.floating_ip

    if new_private_ip != deployed_app.private_ip:
        deployed_app.update_private_ip(deployed_app.name, new_private_ip)
    if new_public_ip != deployed_app.public_ip:
        deployed_app.update_public_ip(new_public_ip)
