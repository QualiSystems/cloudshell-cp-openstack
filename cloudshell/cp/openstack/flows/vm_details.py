from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.flows.vm_details import AbstractVMDetailsFlow
from cloudshell.cp.core.request_actions.models import VmDetailsData

from cloudshell.cp.openstack.models import OSNovaImgDeployedApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.os_api.services import vm_details_provider
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class GetVMDetailsFlow(AbstractVMDetailsFlow):
    def __init__(
        self,
        resource_config: OSResourceConfig,
        cancellation_manager: CancellationContextManager,
        os_api: OSApi,
        logger: Logger,
    ):
        super().__init__(logger)
        self._resource_config = resource_config
        self._cancellation_manager = cancellation_manager
        self._api = os_api

    def _get_vm_details(self, deployed_app: OSNovaImgDeployedApp) -> VmDetailsData:
        instance = self._api.get_instance(deployed_app.vmdetails.uid)
        try:
            result = vm_details_provider.create(
                instance, self._api, self._resource_config.os_mgmt_net_id
            )
        except Exception as e:
            self._logger.exception(f"Error getting VM details for {deployed_app.name}")
            result = VmDetailsData(errorMessage=str(e), appName=instance.name)
        return result
