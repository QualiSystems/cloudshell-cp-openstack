from logging import Logger

import attr

from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.models import OSNovaImgDeployedApp


@attr.s(auto_attribs=True, slots=True)
class PowerFlow:
    _api: OsApi
    _deployed_app: OSNovaImgDeployedApp
    _logger: Logger

    def power_on(self):
        self._api.Instance.get(self._deployed_app.vmdetails.uid).power_on()

    def power_off(self):
        self._api.Instance.get(self._deployed_app.vmdetails.uid).power_off()
