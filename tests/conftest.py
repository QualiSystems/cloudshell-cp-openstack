import json
import time
import uuid
from itertools import cycle
from logging import Logger
from typing import Iterable, Union
from unittest.mock import MagicMock, Mock, create_autospec

import pytest
from keystoneauth1.session import Session as KeyStoneSession
from neutronclient.v2_0.client import Client as NeutronClient

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import DeployVMRequestActions
from cloudshell.shell.core.driver_context import (
    AppContext,
    ConnectivityContext,
    ReservationContextDetails,
    ResourceCommandContext,
    ResourceContextDetails,
)

from cloudshell.cp.openstack.constants import SHELL_NAME
from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.resource_config import OSResourceConfig


@pytest.fixture()
def logger():
    return create_autospec(Logger)


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
    return Mock(name="CS API", DecryptPassword=lambda password: Mock(Value=password))


@pytest.fixture()
def resource_conf(resource_context, cs_api):
    return OSResourceConfig.from_context(SHELL_NAME, resource_context, cs_api)


@pytest.fixture()
def os_session():
    return create_autospec(KeyStoneSession)


@pytest.fixture()
def nova_instance_factory():
    def wrapper(status: Union[str, Iterable[str]]):
        class NovaInstance(MagicMock):
            fault = {"message": "fault message"}

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if isinstance(status, str):
                    self._i_status = cycle(status)
                else:
                    self._i_status = iter(status)

            @property
            def status(self):
                return next(self._i_status)

        return NovaInstance()

    return wrapper


@pytest.fixture()
def nova(nova_instance_factory):
    n = Mock(name="NovaClient")
    n.servers.create.return_value = nova_instance_factory("active")
    return n


@pytest.fixture()
def neutron():
    return create_autospec(NeutronClient)


@pytest.fixture()
def os_api(resource_conf, logger, os_session, nova, neutron, monkeypatch):
    api = OSApi(resource_conf, logger)
    monkeypatch.setattr(api, "_os_session", os_session)
    monkeypatch.setattr(api, "_nova", nova)
    monkeypatch.setattr(api, "_neutron", neutron)
    return api


@pytest.fixture()
def os_api_mock():
    return create_autospec(OSApi)


def get_deploy_app_request(
    app_name="app name",
    image_id="image id",
    instance_flavor="instance flavor",
    add_floating_ip=True,
    floating_ip_subnet_id="floating ip subnet id",
    auto_udev=True,
    user="user",
    password="password",
    public_ip="public ip",
    action_id="action id",
) -> str:
    d_path = "Openstack Shell 2G.OpenStack Deploy Glance Image 2G"
    deployment_conf = {
        "deploymentPath": d_path,
        "attributes": [
            {
                "attributeName": f"{d_path}.Availability Zone",
                "attributeValue": "",
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Image ID",
                "attributeValue": image_id,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Instance Flavor",
                "attributeValue": instance_flavor,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Add Floating IP",
                "attributeValue": add_floating_ip,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Autoload",
                "attributeValue": True,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Affinity Group ID",
                "attributeValue": "",
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Floating IP Subnet ID",
                "attributeValue": floating_ip_subnet_id,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Auto udev",
                "attributeValue": auto_udev,
                "type": "attribute",
            },
            {
                "attributeName": f"{d_path}.Wait for IP",
                "attributeValue": "False",
                "type": "attribute",
            },
        ],
        "type": "deployAppDeploymentInfo",
    }
    app_resource_conf = {
        "attributes": [
            {
                "attributeName": "Password",
                "attributeValue": password,
                "type": "attribute",
            },
            {
                "attributeName": "Public IP",
                "attributeValue": public_ip,
                "type": "attribute",
            },
            {
                "attributeName": "User",
                "attributeValue": user,
                "type": "attribute",
            },
        ],
        "type": "appResourceInfo",
    }
    return json.dumps(
        {
            "driverRequest": {
                "actions": [
                    {
                        "actionParams": {
                            "appName": app_name,
                            "deployment": deployment_conf,
                            "appResource": app_resource_conf,
                            "type": "deployAppParams",
                        },
                        "actionId": action_id,
                        "type": "deployApp",
                    }
                ]
            }
        }
    )


@pytest.fixture()
def deploy_app_request_factory():
    return get_deploy_app_request


@pytest.fixture()
def deploy_app(deploy_app_request_factory, cs_api):
    request = deploy_app_request_factory()

    DeployVMRequestActions.register_deployment_path(OSNovaImgDeployApp)
    request_actions = DeployVMRequestActions.from_request(request, cs_api)
    return request_actions.deploy_app


@pytest.fixture()
def cancellation_context_manager():
    context = Mock(name="cancellation context", is_cancelled=False)
    return CancellationContextManager(context)


@pytest.fixture()
def uuid_mocked(monkeypatch):
    uid = uuid.uuid4()

    def _uuid4():
        return uid

    monkeypatch.setattr(uuid, "uuid4", _uuid4)
    return uid


@pytest.fixture
def sleepless(monkeypatch):
    def sleep(_):
        pass

    monkeypatch.setattr(time, "sleep", sleep)
