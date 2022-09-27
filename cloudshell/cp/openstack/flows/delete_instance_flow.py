from contextlib import suppress

from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.exceptions import FloatingIpNotFound
from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.utils.instance_helpers import (
    get_instance_security_group,
    get_mgmt_iface,
)


def delete_instance(api: OsApi, deployed_app: OSNovaImgDeployedApp):
    inst = api.Instance.get(deployed_app.vmdetails.uid)
    _remove_floating_ip(inst)
    _remove_security_group(inst)
    inst.remove()


def _remove_floating_ip(inst: Instance):
    mgmt_iface = get_mgmt_iface(inst)
    ip_address = mgmt_iface.floating_ip
    if ip_address:
        with suppress(FloatingIpNotFound):
            ip = inst.api.FloatingIp.find_by_ip(ip_address)
            ip.remove()


def _remove_security_group(inst: Instance):
    sg = get_instance_security_group(inst)
    if sg:
        inst.remove_security_group(sg)
        sg.remove()
