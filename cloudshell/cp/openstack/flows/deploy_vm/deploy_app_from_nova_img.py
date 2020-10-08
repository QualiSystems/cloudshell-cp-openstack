from logging import Logger

from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.flows import AbstractDeployFlow
from cloudshell.cp.core.request_actions import DeployVMRequestActions
from cloudshell.cp.core.request_actions.models import Attribute, DeployAppResult

from cloudshell.cp.openstack.models.deploy_app import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api import commands
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.os_api.commands.rollback import RollbackCommandsManager
from cloudshell.cp.openstack.os_api.services import vm_details_provider
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.instance_helpers import get_private_ip


class DeployAppFromNovaImgFlow(AbstractDeployFlow):
    def __init__(
        self,
        resource_conf: OSResourceConfig,
        cancellation_manager: CancellationContextManager,
        os_api: OSApi,
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
                if deploy_app.add_floating_ip:
                    floating_ip = self._create_floating_ip(deploy_app, instance)
                else:
                    floating_ip = ""
                if deploy_app.inbound_ports:
                    self._add_security_group(deploy_app, instance)

                net_name = self._api.get_network_name(
                    self._resource_conf.os_mgmt_net_id
                )
                private_ip = get_private_ip(instance, net_name)
                vm_details_data = vm_details_provider.create(
                    instance, self._api, self._resource_conf.os_mgmt_net_id
                )
                result = DeployAppResult(
                    actionId=deploy_app.actionId,
                    success=True,
                    vmUuid=instance.id,
                    vmName=instance.name,
                    deployedAppAddress=private_ip,
                    deployedAppAttributes=[Attribute("Public IP", floating_ip)],
                    vmDetailsData=vm_details_data,
                )
        except Exception as e:
            self._logger.exception("Error Deploying")
            result = DeployAppResult(
                actionId=deploy_app.actionId, success=False, errorMessage=str(e)
            )
        return result

    def _start_instance(self, deploy_app: OSNovaImgDeployApp) -> NovaServer:
        return commands.CreateInstanceCommand(
            self._rollback_manager, self._cancellation_manager, self._api, deploy_app
        ).execute()

    def _create_floating_ip(
        self, deploy_app: OSNovaImgDeployApp, instance: NovaServer
    ) -> str:
        return commands.CreateFloatingIP(
            self._rollback_manager,
            self._cancellation_manager,
            self._api,
            self._resource_conf,
            deploy_app,
            instance,
        ).execute()

    def _add_security_group(self, deploy_app: OSNovaImgDeployApp, instance: NovaServer):
        return commands.CreateSecurityGroup(
            self._rollback_manager,
            self._cancellation_manager,
            self._api,
            deploy_app,
            instance,
        ).execute()
