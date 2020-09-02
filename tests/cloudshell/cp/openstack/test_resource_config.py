from unittest.mock import MagicMock

import pytest

from cloudshell.shell.core.driver_context import (
    AppContext,
    ConnectivityContext,
    ReservationContextDetails,
    ResourceCommandContext,
    ResourceContextDetails,
)

from cloudshell.cp.openstack.constants import SHELL_NAME
from cloudshell.cp.openstack.resource_config import OSResourceConfig


@pytest.fixture()
def resource_context() -> ResourceCommandContext:
    connectivity = ConnectivityContext(
        server_address="localhost",
        quali_api_port="9000",
        cloudshell_version="2020.1",
        cloudshell_api_scheme="http",
        cloudshell_api_port="8029",
        admin_auth_token="token",
    )
    resource_context_details = ResourceContextDetails(
        address="NA",
        app_context=AppContext(app_request_json="", deployed_app_json=""),
        description="",
        family="Cloud Provider",
        fullname="OpenStack Cloud Provider",
        id="a95027f6-98bf-4177-8d40-d610f0179107",
        model="OpenStack",
        name="OpenStack Cloud Provider",
        networks_info=None,
        shell_standard="",
        shell_standard_version="",
        type="Resource",
        attributes={
            f"{SHELL_NAME}.OpenStack Project Name": "admin",
            f"{SHELL_NAME}.Execution Server Selector": "",
            f"{SHELL_NAME}.OpenStack Physical Interface Name": "",
            f"{SHELL_NAME}.User": "user",
            f"{SHELL_NAME}.OpenStack Domain Name": "default",
            f"{SHELL_NAME}.OpenStack Management Network ID": "9ce15bef-c7a1-4982-910c-0427555236a5",  # noqa: E501
            f"{SHELL_NAME}.Floating IP Subnet ID": "b79772e5-3f2f-4bff-b106-61e666bd65e7",  # noqa: E501
            f"{SHELL_NAME}.OpenStack Reserved Networks": "192.168.1.0/24;192.168.2.0/24",  # noqa: E501
            f"{SHELL_NAME}.Password": "password",
            f"{SHELL_NAME}.VLAN Type": "VXLAN",
            f"{SHELL_NAME}.Controller URL": "http://openstack.example/identity",
        },
    )
    reservation_context = ReservationContextDetails(
        **{
            "domain": "Global",
            "owner_email": None,
            "description": "",
            "environment_name": "CloudShell Sandbox Template3",
            "environment_path": "CloudShell Sandbox Template3",
            "owner_user": "admin",
            "saved_sandbox_id": "",
            "saved_sandbox_name": "",
            "reservation_id": "8574cce6-adba-4e2c-86f7-a146475943c6",
            "running_user": "admin",
        },
    )
    return ResourceCommandContext(
        connectivity, resource_context_details, reservation_context, []
    )


@pytest.fixture()
def cs_api():
    return MagicMock(DecryptPassword=lambda password: MagicMock(Value=password))


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
