from logging import Logger

from cloudshell.cp.openstack.openstack_api.session import get_os_session
from cloudshell.cp.openstack.openstack_api.validator import validate_os_session
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.shell.core.driver_context import AutoLoadDetails


class OpenStackShell:
    """OpenStackShell.

    Methods of this class implement the functionality as required by Shell Driver, which
    provides wrapper over this class.
    """

    def __init__(self):
        pass

    def get_inventory(
        self, resource_config: OSResourceConfig, logger: Logger,
    ):
        os_session = get_os_session(resource_config, logger)
        validate_os_session(os_session, resource_config)
        return AutoLoadDetails([], [])
