from __future__ import annotations

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.rollback import RollbackCommand, RollbackCommandsManager
from cloudshell.cp.core.utils.name_generator import NameGenerator

from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.os_api.models import Instance
from cloudshell.cp.openstack.os_api.services.nova.nova_instance_service import (
    _get_udev_rules,
)
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.instance_helpers import get_mgmt_iface_name

generate_name = NameGenerator()


class CreateInstanceCommand(RollbackCommand):
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        os_api: OsApi,
        deploy_app: OSNovaImgDeployApp,
        resource_conf: OSResourceConfig,
        *args,
        **kwargs,
    ):
        super().__init__(rollback_manager, cancellation_manager, *args, **kwargs)
        self._api = os_api
        self._deploy_app = deploy_app
        self._resource_conf = resource_conf
        self._instance = None

    def _execute(self, *args, **kwargs) -> Instance:
        name = generate_name(self._deploy_app.app_name)
        image = self._api.Image.get(self._deploy_app.image_id)
        flavor = self._api.Flavor.find_first(self._deploy_app.instance_flavor)
        mgmt_net = self._api.Network.get(self._resource_conf.os_mgmt_net_id)

        instance = self._api.Instance.create(
            name,
            image,
            flavor,
            mgmt_net,
            availability_zone=self._deploy_app.availability_zone,
            affinity_group_id=self._deploy_app.affinity_group_id,
            user_data=self._prepare_user_data(),
            cancellation_manager=self._cancellation_manager,
        )
        self._instance = instance
        self._set_mgmt_iface_name(instance)
        return instance

    def rollback(self):
        if isinstance(self._instance, Instance):
            self._instance.remove()

    def _prepare_user_data(self) -> str:
        user_data = ""
        if self._deploy_app.user_data:
            user_data = self._deploy_app.user_data
        if self._deploy_app.auto_udev:
            if user_data:
                user_data += "\n"
            user_data += _get_udev_rules()
        return user_data

    @staticmethod
    def _set_mgmt_iface_name(inst: Instance) -> None:
        ifaces = list(inst.interfaces)
        assert len(ifaces) == 1
        mgmt_iface = ifaces[0]
        mgmt_iface.port.name = get_mgmt_iface_name(inst)
