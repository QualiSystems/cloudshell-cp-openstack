import pytest

from cloudshell.cp.core.request_actions import DeployVMRequestActions

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.models.deploy_app import (
    ResourceInboundPortsRO,
    SecurityGroupRule,
)


def test_deploy_app(deploy_app_request_factory, cs_api):
    app_name = "app name"
    image_id = "image id"
    instance_flavor = "instance flavor"
    add_floating_ip = True
    floating_ip_subnet_id = "floating ip subnet id"
    auto_udev = True
    user = "user"
    password = "password"
    public_ip = "public ip"
    action_id = "action id"
    request = deploy_app_request_factory(
        app_name,
        image_id,
        instance_flavor,
        add_floating_ip,
        floating_ip_subnet_id,
        auto_udev,
        user,
        password,
        public_ip,
        action_id,
    )

    DeployVMRequestActions.register_deployment_path(OSNovaImgDeployApp)
    request_actions = DeployVMRequestActions.from_request(request, cs_api)
    app: OSNovaImgDeployApp = request_actions.deploy_app  # noqa

    assert app.app_name == app_name.replace(" ", "-")
    assert app.image_id == image_id
    assert app.instance_flavor == instance_flavor
    assert app.add_floating_ip == add_floating_ip
    assert app.floating_ip_subnet_id == floating_ip_subnet_id
    assert app.auto_udev == auto_udev
    assert app.user == user
    assert app.password == password
    assert app.public_ip == public_ip
    assert app.actionId == action_id


@pytest.mark.parametrize(
    ("string", "cidr", "protocol", "port_min", "port_max"),
    (
        ("192.168.1.0/24:udp:4500", "192.168.1.0/24", "udp", 4500, 4500),
        ("5000-5100", "0.0.0.0/0", "tcp", 5000, 5100),
        ("10.0.1.0/24:22", "10.0.1.0/24", "tcp", 22, 22),
        ("udp:450", "0.0.0.0/0", "udp", 450, 450),
    ),
)
def test_security_group_rule(string, cidr, protocol, port_min, port_max):
    sgr = SecurityGroupRule.from_str(string)

    assert sgr.cidr == cidr
    assert sgr.protocol == protocol
    assert sgr.port_range_min == port_min
    assert sgr.port_range_max == port_max


@pytest.mark.parametrize("string", ("", "incorrect_cidr:udp:450"))
def test_security_group_incorrect_string(string):
    with pytest.raises(ValueError, match="Security group rule is not supported format"):
        SecurityGroupRule.from_str(string)


def test_resource_inbound_ports_ro():
    class RConfig:
        DEPLOYMENT_PATH = "DP"
        attributes = {"DP.Inbound Ports": "22;udp:4500"}
        inbound_ports = ResourceInboundPortsRO("Inbound Ports")

    assert type(RConfig.inbound_ports) == ResourceInboundPortsRO
    rconf = RConfig()
    assert len(rconf.inbound_ports) == 2
    port1 = rconf.inbound_ports[0]
    assert port1.cidr == "0.0.0.0/0"
    assert port1.protocol == "tcp"
    assert port1.port_range_min == 22
    assert port1.port_range_max == 22
    port2 = rconf.inbound_ports[1]
    assert port2.cidr == "0.0.0.0/0"
    assert port2.protocol == "udp"
    assert port2.port_range_min == 4500
    assert port2.port_range_max == 4500
