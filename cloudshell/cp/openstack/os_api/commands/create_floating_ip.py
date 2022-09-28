from __future__ import annotations

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.api import OsApi
from cloudshell.cp.openstack.os_api.commands.rollback import (
    RollbackCommand,
    RollbackCommandsManager,
)
from cloudshell.cp.openstack.os_api.models import FloatingIp, Interface
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class CreateFloatingIP(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        os_api: OsApi,
        resource_conf: OSResourceConfig,
        deploy_app: OSNovaImgDeployApp,
        iface: Interface,
        *args,
        **kwargs,
    ):
        super().__init__(rollback_manager, cancellation_manager, *args, **kwargs)
        self._api = os_api
        self._resource_conf = resource_conf
        self._deploy_app = deploy_app
        self._iface = iface
        self._ip: FloatingIp | None = None

    def _execute(self, *args, **kwargs) -> str:
        if self._deploy_app.floating_ip_subnet_id:
            subnet_id = self._deploy_app.floating_ip_subnet_id
        else:
            subnet_id = self._resource_conf.floating_ip_subnet_id
        floating_subnet = self._api.Subnet.get(subnet_id)

        ip = self._api.FloatingIp.create(floating_subnet, self._iface.port)
        self._ip = ip
        return ip.ip_address

    def rollback(self):
        if isinstance(self._ip, FloatingIp):
            self._ip.remove()
