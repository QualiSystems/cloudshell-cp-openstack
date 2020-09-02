from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.os_api.commands.rollback import (
    RollbackCommand,
    RollbackCommandsManager,
)
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class CreateFloatingIP(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        os_api: OSApi,
        resource_conf: OSResourceConfig,
        deploy_app: OSNovaImgDeployApp,
        instance: NovaServer,
        *args,
        **kwargs,
    ):
        super().__init__(rollback_manager, cancellation_manager, *args, **kwargs)
        self._api = os_api
        self._resource_conf = resource_conf
        self._deploy_app = deploy_app
        self._instance = instance
        self._ip = ""

    def _execute(self, *args, **kwargs):
        if self._deploy_app.floating_ip_subnet_id:
            subnet_id = self._deploy_app.floating_ip_subnet_id
        else:
            subnet_id = self._resource_conf.floating_ip_subnet_id
        port_id = self._instance.interface_list()[0].port_id
        self._ip = self._api.create_floating_ip(subnet_id, port_id)
        return self._ip

    def rollback(self):
        self._api.delete_floating_ip(self._ip)
