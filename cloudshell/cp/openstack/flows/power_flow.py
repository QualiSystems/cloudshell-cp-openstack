from logging import Logger

from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.utils.cached_property import cached_property


class PowerFlow:
    def __init__(
        self,
        os_api: OSApi,
        deployed_app: OSNovaImgDeployedApp,
        logger: Logger,
    ):
        self._api = os_api
        self._deployed_app = deployed_app
        self._logger = logger

    @cached_property
    def _instance(self):
        return self._api.get_instance(self._deployed_app.vmdetails.uid)

    def power_on(self):
        self._api.power_on_instance(self._instance)

    def power_off(self):
        self._api.power_off_instance(self._instance)
