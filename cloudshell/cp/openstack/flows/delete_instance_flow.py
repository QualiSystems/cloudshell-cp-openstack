from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OSApi


def delete_instance(api: OSApi, deployed_app: OSNovaImgDeployedApp):
    instance = api.get_instance(deployed_app.vmdetails.uid)
    if deployed_app.public_ip:
        api.delete_floating_ip(deployed_app.public_ip)
    api.delete_security_group_for_instance(instance)
    api.terminate_instance(instance)
