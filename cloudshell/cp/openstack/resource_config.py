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


class ResourceListAttrRO(ResourceAttrRO):
    def __init__(self, name, namespace, *args, sep=";", **kwargs):
        super().__init__(name, namespace, *args, **kwargs)
        self._sep = sep

    def __get__(self, instance, owner) -> List[str]:
        values = super().__get__(instance, owner)
        return list(filter(bool, map(str.strip, values.split(self._sep))))


class OSAttributeNames:
    controller_url = "Controller URL"
    os_domain_name = "OpenStack Domain Name"
    os_project_name = "OpenStack Project Name"
    username = "User Name"
    password = "Password"
    os_reserved_networks = "OpenStack Reserved Networks"
    os_mgmt_net_id = "OpenStack Management Network ID"
    vlan_type = "Vlan Type"
    os_physical_int_name = "OpenStack Physical Interface Name"
    floating_ip_subnet_id = "Floating IP Subnet ID"
    exec_server_selector = "Execution Server Selector"


class OSResourceConfig(GenericResourceConfig):
    ATTR_NAMES = OSAttributeNames
    controller_url = ResourceAttrROShellName(ATTR_NAMES.controller_url)
    os_domain_name = ResourceAttrROShellName(ATTR_NAMES.os_domain_name)
    os_project_name = ResourceAttrROShellName(ATTR_NAMES.os_project_name)
    username = ResourceAttrROShellName(ATTR_NAMES.username)
    password = PasswordAttrRO(ATTR_NAMES.password, ResourceAttrRO.NAMESPACE.SHELL_NAME)
    os_reserved_networks = ResourceListAttrRO(
        ATTR_NAMES.os_reserved_networks, ResourceListAttrRO.NAMESPACE.SHELL_NAME
    )
    os_mgmt_net_id = ResourceAttrROShellName(ATTR_NAMES.os_mgmt_net_id)
    vlan_type = ResourceAttrROShellName(ATTR_NAMES.vlan_type)
    os_physical_int_name = ResourceAttrROShellName(ATTR_NAMES.os_physical_int_name)
    floating_ip_subnet_id = ResourceAttrROShellName(ATTR_NAMES.floating_ip_subnet_id)
    exec_server_selector = ResourceAttrROShellName(ATTR_NAMES.exec_server_selector)

    @classmethod
    def from_context(
        cls,
        shell_name: str,
        context: Union[AutoLoadCommandContext],
        api: Optional[CloudShellAPISession] = None,
        supported_os: Optional[List[str]] = None,
    ) -> "OSResourceConfig":
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
