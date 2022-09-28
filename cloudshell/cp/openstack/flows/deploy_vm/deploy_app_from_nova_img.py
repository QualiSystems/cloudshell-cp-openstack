from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.flows import AbstractDeployFlow
from cloudshell.cp.core.request_actions import DeployVMRequestActions
from cloudshell.cp.core.request_actions.models import Attribute, DeployAppResult

from cloudshell.cp.openstack.models.deploy_app import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api import commands
from cloudshell.cp.openstack.os_api.api import OsApi
from cloudshell.cp.openstack.os_api.commands.rollback import RollbackCommandsManager
from cloudshell.cp.openstack.os_api.models import Instance, Interface
from cloudshell.cp.openstack.os_api.services import vm_details_provider
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class DeployAppFromNovaImgFlow(AbstractDeployFlow):
    def __init__(
        self,
        resource_conf: OSResourceConfig,
        cancellation_manager: CancellationContextManager,
        os_api: OsApi,
        logger: Logger,
    ):
        super().__init__(logger)
        self._resource_conf = resource_conf
        self._cancellation_manager = cancellation_manager
        self._api = os_api
        self._rollback_manager = RollbackCommandsManager(logger)

    def _deploy(self, request_actions: DeployVMRequestActions) -> DeployAppResult:
        self._logger.info("Start Deploy Operation")
        deploy_app: OSNovaImgDeployApp = request_actions.deploy_app
        try:
            with self._rollback_manager:
                instance = self._start_instance(deploy_app)
                mgmt_iface = next(instance.interfaces)  # we have one iface on deploy
                if deploy_app.add_floating_ip:
                    floating_ip = self._create_floating_ip(deploy_app, mgmt_iface)
                else:
                    floating_ip = ""
                if deploy_app.inbound_ports:
                    self._add_security_group(deploy_app, instance)

                vm_details_data = vm_details_provider.create(
                    instance, self._resource_conf.os_mgmt_net_id
                )
                result = DeployAppResult(
                    actionId=deploy_app.actionId,
                    success=True,
                    vmUuid=instance.id,
                    vmName=instance.name,
                    deployedAppAddress=mgmt_iface.fixed_ip,
                    deployedAppAttributes=[Attribute("Public IP", floating_ip)],
                    vmDetailsData=vm_details_data,
                )
        except Exception as e:
            self._logger.exception("Error Deploying")
            result = DeployAppResult(
                actionId=deploy_app.actionId, success=False, errorMessage=str(e)
            )
        return result

    def _start_instance(self, deploy_app: OSNovaImgDeployApp) -> Instance:
        return commands.CreateInstanceCommand(
            self._rollback_manager,
            self._cancellation_manager,
            self._api,
            deploy_app,
            self._resource_conf,
        ).execute()

    def _create_floating_ip(
        self, deploy_app: OSNovaImgDeployApp, iface: Interface
    ) -> str:
        return commands.CreateFloatingIP(
            self._rollback_manager,
            self._cancellation_manager,
            self._api,
            self._resource_conf,
            deploy_app,
            iface,
        ).execute()

    def _add_security_group(self, deploy_app: OSNovaImgDeployApp, instance: Instance):
        return commands.CreateSecurityGroup(
            self._rollback_manager,
            self._cancellation_manager,
            self._api,
            deploy_app,
            instance,
        ).execute()
