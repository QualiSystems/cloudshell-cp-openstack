from __future__ import annotations

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.api import OsApi
from cloudshell.cp.openstack.os_api.commands.rollback import (
    RollbackCommand,
    RollbackCommandsManager,
)
from cloudshell.cp.openstack.os_api.models import Instance, SecurityGroup


class CreateSecurityGroup(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        os_api: OsApi,
        deploy_app: OSNovaImgDeployApp,
        instance: Instance,
        *args,
        **kwargs,
    ):
        super().__init__(rollback_manager, cancellation_manager, *args, **kwargs)
        self._api = os_api
        self._deploy_app = deploy_app
        self._instance = instance
        self._sg: SecurityGroup | None = None

    def _execute(self, *args, **kwargs) -> SecurityGroup:
        name = f"sg-{self._instance.name}"
        sg = self._api.SecurityGroup.create(name)

        try:
            self._add_rules(sg)
            self._instance.add_security_group(sg)
        except Exception:
            sg.remove()
            raise

        self._sg = sg
        return sg

    def _add_rules(self, sg: SecurityGroup) -> None:
        for rule in self._deploy_app.inbound_ports:
            sg.add_rule(
                cidr=rule.cidr,
                protocol=rule.protocol,
                port_range_min=rule.port_range_min,
                port_range_max=rule.port_range_max,
                direction="ingress",
            )

    def rollback(self):
        if self._sg:
            self._instance.remove_security_group(self._sg)
            self._sg.remove()
