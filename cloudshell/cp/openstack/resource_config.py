from functools import partial
from typing import List, Optional, Union

from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.shell.core.driver_context import AutoLoadCommandContext
from cloudshell.shell.standards.core.resource_config_entities import (
    GenericResourceConfig,
    PasswordAttrRO,
    ResourceAttrRO,
)

ResourceAttrROShellName = partial(
    ResourceAttrRO, namespace=ResourceAttrRO.NAMESPACE.SHELL_NAME
)


class OpenStackResourceConfig(GenericResourceConfig):
    controller_url = ResourceAttrROShellName("Controller URL")
    openstack_domain_name = ResourceAttrROShellName("OpenStack Domain Name")
    openstack_project_name = ResourceAttrROShellName("OpenStack Project Name")
    username = ResourceAttrROShellName("User Name")
    password = PasswordAttrRO("Password", ResourceAttrRO.NAMESPACE.SHELL_NAME)
    openstack_reserved_networks = ResourceAttrROShellName("OpenStack Reserved Networks")
    openstack_management_network_id = ResourceAttrROShellName(
        "OpenStack Management Network ID"
    )
    vlan_type = ResourceAttrROShellName("Vlan Type")
    openstack_physical_interface_name = ResourceAttrROShellName(
        "OpenStack Physical Interface Name"
    )
    floating_ip_subnet_id = ResourceAttrROShellName("Floating IP Subnet ID")
    execution_server_selector = ResourceAttrROShellName("Execution Server Selector")

    @classmethod
    def from_context(
        cls,
        shell_name: str,
        context: Union[AutoLoadCommandContext],
        api: Optional[CloudShellAPISession] = None,
        supported_os: Optional[List[str]] = None,
    ) -> "OpenStackResourceConfig":
        return cls(
            shell_name=shell_name,
            name=context.resource.name,
            fullname=context.resource.fullname,
            address=context.resource.address,
            family_name=context.resource.family,
            attributes=dict(context.resource.attributes),
            supported_os=supported_os,
            api=api,
        )
