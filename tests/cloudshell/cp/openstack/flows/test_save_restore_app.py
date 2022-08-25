import json
from unittest.mock import call

import pytest

from cloudshell.cp.core.request_actions.models import (
    Artifact,
    Attribute,
    DeleteSavedApp,
    DeleteSavedAppParams,
    SaveApp,
    SaveAppParams,
)

from cloudshell.cp.openstack.constants import OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH
from cloudshell.cp.openstack.flows.save_restore_app import SaveRestoreAppFlow
from cloudshell.cp.openstack.models.attr_names import ResourceAttrName


@pytest.fixture()
def save_restore_flow(resource_conf, logger, cancellation_context_manager, os_api_v2):
    return SaveRestoreAppFlow(
        resource_conf, logger, cancellation_context_manager, os_api_v2
    )


def test_save_app(save_restore_flow, instance):
    action_id = "action id"
    vm_uuid = "vm uuid"
    snapshot_id = "snapshot id"
    action = SaveApp(
        action_id,
        SaveAppParams(
            saveDeploymentModel="",
            savedSandboxId="",
            sourceVmUuid=vm_uuid,
            sourceAppName="",
            deploymentPathAttributes=[
                Attribute(
                    attributeName=ResourceAttrName.behavior_during_save,
                    attributeValue="Power Off",
                )
            ],
        ),
    )
    instance.create_image.return_value = snapshot_id

    result = save_restore_flow.save_apps([action])

    expected_result = {
        "driverResponse": {
            "actionResults": [
                {
                    "actionId": action_id,
                    "additionalData": [],
                    "artifacts": [
                        {
                            "artifactName": ResourceAttrName.image_id,
                            "artifactRef": snapshot_id,
                        }
                    ],
                    "errorMessage": "",
                    "infoMessage": "",
                    "saveDeploymentModel": OS_FROM_GLANCE_IMAGE_DEPLOYMENT_PATH,
                    "savedEntityAttributes": [
                        {
                            "attributeName": ResourceAttrName.image_id,
                            "attributeValue": snapshot_id,
                        }
                    ],
                    "success": True,
                    "type": "SaveApp",
                }
            ]
        }
    }
    assert json.loads(result) == expected_result
    instance.assert_has_calls(
        [call.stop(), call.create_image(f"Clone of {instance.name}"), call.start()]
    )


def test_delete_saved_apps(save_restore_flow, glance):
    action_id = "action id"
    snapshot_id = "snapshot id"
    action = DeleteSavedApp(
        action_id,
        DeleteSavedAppParams(
            saveDeploymentModel="",
            savedSandboxId="",
            artifacts=[
                Artifact(
                    artifactRef=snapshot_id, artifactName=ResourceAttrName.image_id
                )
            ],
            savedAppName="",
        ),
    )

    save_restore_flow.delete_saved_apps([action])

    glance.images.delete(snapshot_id)
