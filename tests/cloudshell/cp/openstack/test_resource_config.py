from cloudshell.shell.core.driver_context import ResourceCommandContext

from cloudshell.cp.openstack.constants import SHELL_NAME
from cloudshell.cp.openstack.resource_config import OSResourceConfig


def test_parse_resource_conf(resource_context: ResourceCommandContext, cs_api):
    conf = OSResourceConfig.from_context(SHELL_NAME, resource_context, cs_api)
    assert conf.os_project_name == "admin"
    assert conf.exec_server_selector == ""
    assert conf.os_physical_int_name == ""
    assert conf.user == "user"
    assert conf.os_domain_name == "default"
    assert conf.os_mgmt_net_id == "9ce15bef-c7a1-4982-910c-0427555236a5"
    assert conf.floating_ip_subnet_id == "b79772e5-3f2f-4bff-b106-61e666bd65e7"
    assert conf.os_reserved_networks == ["192.168.1.0/24", "192.168.2.0/24"]
    assert conf.password == "password"
    assert conf.vlan_type == "VXLAN"
    assert conf.controller_url == "http://openstack.example/identity"
