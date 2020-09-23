import re
from unittest.mock import Mock, patch

import pytest

from cloudshell.cp.openstack.os_api.services.validator import (
    _is_http_url,
    _is_not_empty,
    _is_one_of_the,
    _validate_resource_conf,
)


@pytest.mark.parametrize("val,err", (("val", False), ("", True)))
def test_is_not_empty(val, err):
    if err is False:
        assert _is_not_empty(val, "attr name") is None
    else:
        with pytest.raises(ValueError, match="attr name cannot be empty"):
            _is_not_empty(val, "attr name")


@pytest.mark.parametrize(
    "val,err",
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
    "val,expected_vals,err",
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
