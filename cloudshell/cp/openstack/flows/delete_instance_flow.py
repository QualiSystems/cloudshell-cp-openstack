from contextlib import suppress

from cloudshell.cp.openstack.exceptions import FloatingIpNotFound
from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OsApi
from cloudshell.cp.openstack.os_api.models import Instance, Interface
from cloudshell.cp.openstack.utils.instance_helpers import (
    get_instance_security_group,
    get_mgmt_iface,
)


def delete_instance(api: OsApi, deployed_app: OSNovaImgDeployedApp):
    inst = api.Instance.get(deployed_app.vmdetails.uid)
    mgmt_iface = get_mgmt_iface(inst)
    _remove_floating_ip(mgmt_iface)
    _remove_security_group(inst)
    inst.remove()
    _remove_port_for_private_ip(deployed_app, mgmt_iface)


def _remove_floating_ip(mgmt_iface: Interface) -> None:
    ip_address = mgmt_iface.floating_ip
    if ip_address:
        with suppress(FloatingIpNotFound):
            ip = mgmt_iface.api.FloatingIp.find_by_ip(ip_address)
            ip.remove()


def _remove_security_group(inst: Instance) -> None:
    sg = get_instance_security_group(inst)
    if sg:
        inst.remove_security_group(sg)
        sg.remove()


def _remove_port_for_private_ip(
    deployed_app: OSNovaImgDeployedApp, mgmt_iface: Interface
) -> None:
    if deployed_app.private_ip:
        mgmt_iface.port.remove()
