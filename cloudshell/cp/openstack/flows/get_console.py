from cloudshell.cp.openstack.exceptions import NotSupportedConsoleType
from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OsApi

CONSOLE_TYPES = {
    "Instance Console": "novnc",  # http://url
    "Serial WebSocket Console": "serial",  # ws://url
}


def validate_console_type(console_type: str):
    if console_type not in CONSOLE_TYPES:
        raise NotSupportedConsoleType(console_type, CONSOLE_TYPES)


def get_console(
    api: OsApi, deployed_app: OSNovaImgDeployedApp, console_type: str
) -> str:
    inst = api.Instance.get(deployed_app.vmdetails.uid)
    os_console_type = CONSOLE_TYPES[console_type]
    return inst.get_console_url(os_console_type)
