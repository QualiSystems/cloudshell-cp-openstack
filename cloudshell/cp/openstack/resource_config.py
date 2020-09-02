from cloudshell.shell.standards.core.resource_config_entities import (
    GenericResourceConfig,
    PasswordAttrRO,
    ResourceAttrRO,
    ResourceListAttrRO,
)


class ResourceAttrROShellName(ResourceAttrRO):
    def __init__(self, name, namespace=ResourceAttrRO.NAMESPACE.SHELL_NAME):
        super().__init__(name, namespace)


class ResourceListAttrROShellName(ResourceListAttrRO):
    def __init__(
        self, name, namespace=ResourceListAttrRO.NAMESPACE.SHELL_NAME, *args, **kwargs
    ):
        super().__init__(name, namespace, *args, **kwargs)


class OSAttributeNames:
    controller_url = "Controller URL"
    os_domain_name = "OpenStack Domain Name"
    os_project_name = "OpenStack Project Name"
    user = "User"
    password = "Password"
    os_reserved_networks = "OpenStack Reserved Networks"
    os_mgmt_net_id = "OpenStack Management Network ID"
    vlan_type = "VLAN Type"
    os_physical_int_name = "OpenStack Physical Interface Name"
    floating_ip_subnet_id = "Floating IP Subnet ID"
    exec_server_selector = "Execution Server Selector"


class OSResourceConfig(GenericResourceConfig):
    ATTR_NAMES = OSAttributeNames
    controller_url = ResourceAttrROShellName(ATTR_NAMES.controller_url)
    os_domain_name = ResourceAttrROShellName(ATTR_NAMES.os_domain_name)
    os_project_name = ResourceAttrROShellName(ATTR_NAMES.os_project_name)
    user = ResourceAttrROShellName(ATTR_NAMES.user)
    password = PasswordAttrRO(ATTR_NAMES.password, ResourceAttrRO.NAMESPACE.SHELL_NAME)
    os_reserved_networks = ResourceListAttrROShellName(ATTR_NAMES.os_reserved_networks)
    os_mgmt_net_id = ResourceAttrROShellName(ATTR_NAMES.os_mgmt_net_id)
    vlan_type = ResourceAttrROShellName(ATTR_NAMES.vlan_type)
    os_physical_int_name = ResourceAttrROShellName(ATTR_NAMES.os_physical_int_name)
    floating_ip_subnet_id = ResourceAttrROShellName(ATTR_NAMES.floating_ip_subnet_id)
    exec_server_selector = ResourceAttrROShellName(ATTR_NAMES.exec_server_selector)
