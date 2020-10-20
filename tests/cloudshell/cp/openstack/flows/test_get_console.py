from contextlib import nullcontext

import pytest

from cloudshell.cp.openstack.exceptions import NotSupportedConsoleType
from cloudshell.cp.openstack.flows import get_console, validate_console_type


@pytest.mark.parametrize(
    ("console_type", "error"),
    (
        ("Instance Console", None),
        ("Serial WebSocket Console", None),
        ("another", NotSupportedConsoleType),
    ),
)
def test_validate_console_type(console_type, error):
    if error:
        context = pytest.raises(error, match="not supported")
    else:
        context = nullcontext()

    with context:
        validate_console_type(console_type)


def test_get_console(os_api, deployed_app, nova, instance):
    result = get_console(os_api, deployed_app, "Instance Console")

    nova.servers.find.assert_called_once_with(id=deployed_app.vmdetails.uid)
    instance.get_console_url.assert_called_once_with("novnc")
    assert result == instance.get_console_url()["console"]["url"]
