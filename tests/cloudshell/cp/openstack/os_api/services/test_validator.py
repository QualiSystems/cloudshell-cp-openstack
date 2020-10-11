import re
from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from keystoneauth1 import exceptions as keystone_exceptions
from neutronclient.client import exceptions as neutron_exceptions

from cloudshell.cp.openstack.os_api.services.validator import (
    _get_network_dict,
    _is_http_url,
    _is_not_empty,
    _is_one_of_the,
    _validate_connection,
    _validate_floating_ip_subnet,
    _validate_network_attributes,
    _validate_reserved_networks,
    _validate_resource_conf,
    _validate_vlan_type,
    validate_conf_and_connection,
)


@pytest.mark.parametrize(("val", "err"), (("val", False), ("", True)))
def test_is_not_empty(val, err):
    if err is False:
        assert _is_not_empty(val, "attr name") is None
    else:
        with pytest.raises(ValueError, match="attr name cannot be empty"):
            _is_not_empty(val, "attr name")


@pytest.mark.parametrize(
    ("val", "err"),
    (
        ("http://example.com", False),
        ("https://example.com", False),
        ("htp://example.com", True),
        ("example.com", True),
    ),
)
def test_is_http_url(val, err):
    if err is False:
        assert _is_http_url(val, "url") is None
    else:
        with pytest.raises(ValueError, match=f"{val} is not valid format for url"):
            _is_http_url(val, "url")


@pytest.mark.parametrize(
    ("val", "expected_vals", "err"),
    (("vlan", ("VLAN", "VXLAN"), False), ("lan", ("VLAN", "VXLAN"), True)),
)
def test_is_one_of_the(val, expected_vals, err):
    if err is False:
        assert _is_one_of_the(val, expected_vals, "attr name") is None
    else:
        err_msg = re.escape(f"attr name should be one of {expected_vals}")
        with pytest.raises(ValueError, match=err_msg):
            _is_one_of_the(val, expected_vals, "attr name")


def test_validate_resource_conf():
    resource_conf = Mock()
    with patch(
        "cloudshell.cp.openstack.os_api.services.validator._is_http_url"
    ) as is_http_url_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._is_not_empty"
    ) as is_not_empty_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._is_one_of_the"
    ) as is_one_of_the_mock:
        # run
        _validate_resource_conf(resource_conf)

        # validate
        is_not_empty_mock.assert_any_call(
            resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.os_domain_name, resource_conf.ATTR_NAMES.os_domain_name
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.os_project_name, resource_conf.ATTR_NAMES.os_project_name
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.user, resource_conf.ATTR_NAMES.user
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.password, resource_conf.ATTR_NAMES.password
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.os_mgmt_net_id, resource_conf.ATTR_NAMES.os_mgmt_net_id
        )
        is_not_empty_mock.assert_any_call(
            resource_conf.floating_ip_subnet_id,
            resource_conf.ATTR_NAMES.floating_ip_subnet_id,
        )

        is_http_url_mock.assert_called_once_with(
            resource_conf.controller_url, resource_conf.ATTR_NAMES.controller_url
        )

        is_one_of_the_mock.assert_called_once_with(
            resource_conf.vlan_type,
            ("VLAN", "VXLAN"),
            resource_conf.ATTR_NAMES.vlan_type,
        )


def test_validate_connection(os_api, nova, resource_conf):
    _validate_connection(os_api, resource_conf)
    nova.servers.list.assert_called_once_with()


@pytest.mark.parametrize(
    ("handled_error", "raised_error", "err_msg_pattern"),
    (
        (keystone_exceptions.http.BadRequest, keystone_exceptions.http.BadRequest, ""),
        (
            keystone_exceptions.http.Unauthorized,
            keystone_exceptions.http.Unauthorized,
            "",
        ),
        (
            keystone_exceptions.http.NotFound,
            ValueError,
            "Controller URL .+ is not found",
        ),
        (Exception, Exception, "One or more values are not correct"),
    ),
)
def test_validate_connection_errors(
    handled_error, raised_error, err_msg_pattern, os_api, nova, resource_conf
):
    nova.servers.list.side_effect = handled_error
    with pytest.raises(raised_error, match=err_msg_pattern):
        _validate_connection(os_api, resource_conf)


def test_network_dict_fails(os_api_mock):
    os_api_mock.get_network_dict.side_effect = Exception()
    net_id = "network id"
    with pytest.raises(ValueError, match="Error getting network"):
        _get_network_dict(os_api_mock, net_id)
    os_api_mock.get_network_dict.assert_called_once_with(id=net_id)


@pytest.mark.parametrize(
    ("network_dict", "error"),
    (({"router:external": True}, None), ({"router:external": False}, ValueError)),
)
def test_validate_floating_ip_subnet(os_api_mock, network_dict, error):
    net_id = "network id"
    subnet_id = "subnet id"
    os_api_mock.get_network_id_for_subnet_id.return_value = net_id
    os_api_mock.get_network_dict.return_value = network_dict

    if error is not None:
        context = pytest.raises(error, match="not an external network")
    else:
        context = nullcontext()

    with context:
        _validate_floating_ip_subnet(os_api_mock, subnet_id)

    os_api_mock.get_network_id_for_subnet_id.assert_called_once_with(subnet_id)
    os_api_mock.get_network_dict.assert_called_once_with(id=net_id)


@pytest.mark.parametrize(
    ("create_net_dict_side_effect",),
    (
        ([{"network": {"id": "net id"}}],),
        (
            [
                neutron_exceptions.Conflict,
                neutron_exceptions.Conflict,
                {"network": {"id": "net id"}},
            ],
        ),
    ),
)
def test_validate_vlan_type(os_api_mock, create_net_dict_side_effect):
    net_id = "net id"
    vlan_type = "VLAN"
    physical_int = "ethernet-1"
    os_api_mock.create_network.side_effect = create_net_dict_side_effect

    _validate_vlan_type(os_api_mock, vlan_type, physical_int)

    os_api_mock.remove_network.assert_called_once_with(net_id)
    assert os_api_mock.create_network.call_count == len(create_net_dict_side_effect)
    data = os_api_mock.create_network.call_args[0][0]["network"]
    assert data["provider:network_type"] == vlan_type.lower()
    assert data["name"] == "qs_autoload_validation_net"
    assert data["admin_state_up"] is True
    assert data["provider:physical_network"] == physical_int


@pytest.mark.parametrize(
    "error", (Exception("You missed physical int"), neutron_exceptions.Conflict(""))
)
def test_validate_vlan_type_create_network_raised(os_api_mock, error):
    os_api_mock.create_network.side_effect = error

    r = " after 10 retries" if isinstance(error, neutron_exceptions.Conflict) else ""
    emsg = f"Error occurred during creating network{r}. {error}"
    with pytest.raises(ValueError, match=emsg):
        _validate_vlan_type(os_api_mock, "VLAN", "")
    os_api_mock.create_network.assert_called()
    os_api_mock.remove_network.assert_not_called()


@pytest.mark.parametrize(
    ("net_list", "error"),
    (
        (["192.168.1.0/24"], None),
        (["2001:0db8:85a3:0000:0000:8a2e:0370:7334"], None),
        (["192.168.1"], ValueError("does not appear to be an IPv4 or IPv6 network")),
    ),
)
def test_validate_reserved_networks(net_list, error):
    if error is None:
        context = nullcontext()
    else:
        context = pytest.raises(type(error), match=str(error))

    with context:
        _validate_reserved_networks(net_list)


def test_validate_network_attributes(os_api_mock):
    resource_conf = Mock()
    with patch(
        "cloudshell.cp.openstack.os_api.services.validator._get_network_dict"
    ) as get_network_dict_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_floating_ip_subnet"
    ) as validate_floating_ip_subnet_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_vlan_type"
    ) as validate_vlan_type_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_reserved_networks"
    ) as validate_reserved_networks_mock:
        # run
        _validate_network_attributes(os_api_mock, resource_conf)

        # validate
        get_network_dict_mock.assert_called_once_with(
            os_api_mock, resource_conf.os_mgmt_net_id
        )
        validate_floating_ip_subnet_mock.assert_called_once_with(
            os_api_mock, resource_conf.floating_ip_subnet_id
        )
        validate_vlan_type_mock.assert_called_once_with(
            os_api_mock, resource_conf.vlan_type, resource_conf.os_physical_int_name
        )
        validate_reserved_networks_mock.assert_called_once_with(
            resource_conf.os_reserved_networks
        )


def test_validate_conf_and_connection(os_api_mock):
    resource_conf = Mock()
    with patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_resource_conf"
    ) as validate_resource_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_connection"
    ) as validate_connection_mock, patch(
        "cloudshell.cp.openstack.os_api.services.validator._validate_network_attributes"
    ) as validate_network_attributes_mock:
        # run
        validate_conf_and_connection(os_api_mock, resource_conf)

        # validate
        validate_resource_mock.assert_called_once_with(resource_conf)
        validate_connection_mock.assert_called_once_with(os_api_mock, resource_conf)
        validate_network_attributes_mock.assert_called_once_with(
            os_api_mock, resource_conf
        )
