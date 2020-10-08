from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.os_api.commands.rollback import (
    RollbackCommand,
    RollbackCommandsManager,
)


class CreateSecurityGroup(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        os_api: OSApi,
        deploy_app: OSNovaImgDeployApp,
        instance: NovaServer,
        *args,
        **kwargs,
    ):
        super().__init__(rollback_manager, cancellation_manager, *args, **kwargs)
        self._api = os_api
        self._deploy_app = deploy_app
        self._instance = instance
        self._sg_id = ""

    def _execute(self, *args, **kwargs):
        self._sg_id = self._api.create_security_group_for_instance(
            self._instance, self._deploy_app.inbound_ports
        )

    def rollback(self):
        self._api.delete_security_group_for_instance(self._instance)
