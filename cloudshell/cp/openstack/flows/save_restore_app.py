from logging import Logger
from typing import Iterable

import attr

from cloudshell.cp.core.cancellation_manager import CancellationContextManager
from cloudshell.cp.core.request_actions import DriverResponse
from cloudshell.cp.core.request_actions.models import (
    Artifact,
    Attribute,
    DeleteSavedApp,
    DeleteSavedAppResult,
    SaveApp,
    SaveAppResult,
)

from cloudshell.cp.openstack.constants import OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH
from cloudshell.cp.openstack.models.attr_names import ResourceAttrName
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.resource_config import OSResourceConfig


@attr.s(auto_attribs=True, slots=True, frozen=True)
class SaveRestoreAppFlow:
    _api: OSApi
    _resource_conf: OSResourceConfig
    _logger: Logger
    _cancellation_manager: CancellationContextManager

    def save_apps(self, save_actions: Iterable[SaveApp]) -> str:
        results = list(map(self._save_app, save_actions))
        return DriverResponse(results).to_driver_response_json()

    def delete_saved_apps(
        self, delete_saved_app_actions: Iterable[DeleteSavedApp]
    ) -> str:
        results = list(map(self._delete_saved_app, delete_saved_app_actions))
        return DriverResponse(results).to_driver_response_json()

    def _save_app(self, save_action: SaveApp) -> SaveAppResult:
        self._logger.info(f"Starting save app {save_action.actionParams.sourceAppName}")
        self._logger.debug(f"Save action model: {save_action}")

        vm_uuid = save_action.actionParams.sourceVmUuid
        attrs = {
            a.attributeName.rsplit(".", 1)[-1]: a.attributeValue
            for a in save_action.actionParams.deploymentPathAttributes
        }

        with self._cancellation_manager:
            instance = self._api.get_instance(vm_uuid)

        if attrs[ResourceAttrName.behavior_during_save] == "Power Off":
            self._api.power_off_instance(instance)

        snapshot_name = f"Clone of {instance.name[:64]}"
        snapshot_id = self._api.create_snapshot(instance, snapshot_name)

        if attrs[ResourceAttrName.behavior_during_save] == "Power Off":
            self._api.power_on_instance(instance)

        return SaveAppResult(
            save_action.actionId,
            artifacts=[Artifact(snapshot_id, ResourceAttrName.image_id)],
            savedEntityAttributes=[Attribute(ResourceAttrName.image_id, snapshot_id)],
            saveDeploymentModel=OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH,
        )

    def _delete_saved_app(self, action: DeleteSavedApp) -> DeleteSavedAppResult:
        for artifact in action.actionParams.artifacts:
            snapshot_id = artifact.artifactRef
            with self._cancellation_manager:
                self._api.remove_image(snapshot_id)

        return DeleteSavedAppResult(action.actionId)
