import time
import uuid
from contextlib import nullcontext
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import ContextManager

from novaclient import exceptions as nova_exceptions
from novaclient.v2.client import Client as NovaClient
from novaclient.v2.flavors import Flavor
from novaclient.v2.images import Image
from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.exceptions import InstanceErrorStateException
from cloudshell.cp.openstack.models.deploy_app import OSNovaImgDeployApp
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class NovaInstanceStatus(Enum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    BUILDING = "BUILDING"
    STOPPED = "STOPPED"
    DELETED = "DELETED"
    SHUTOFF = "SHUTOFF"
    OTHER = "_OTHER"

    @classmethod
    def _missing_(cls, value: str):
        status = cls.__members__.get(value.upper(), cls.OTHER)
        if status is cls.OTHER:
            status._real_value = value
        return status


class NovaService:
    """Implements management of Compute Instances."""

    API_VERSION = "2"
    STATUS = NovaInstanceStatus
    WAIT_DELAY = 10

    def __init__(self, instance: NovaServer, nova: NovaClient, logger: Logger):
        self.instance = instance
        self._nova = nova
        self._logger = logger

    @classmethod
    def create_instance(
        cls,
        nova: NovaClient,
        resource_conf: OSResourceConfig,
        deploy_app: OSNovaImgDeployApp,
        cancellation_manager: CancellationContextManager,
        logger: Logger,
    ) -> "NovaService":
        if not deploy_app.instance_flavor:
            raise ValueError("Instance flavor cannot be empty.")
        logger.info(
            f"Creating OpenStack Instance for Image: {deploy_app.image_id}, "
            f"Flavor: {deploy_app.instance_flavor}"
        )
        create_args = cls._prepare_creating_args(deploy_app, resource_conf, nova)
        instance = nova.servers.create(**create_args)
        with cancellation_manager:
            instance_service = cls(instance, nova, logger)
        try:
            instance_service._wait_for_status(
                cls.STATUS.ACTIVE, cancellation_manager=cancellation_manager
            )
        except Exception:
            logger.exception("Failed to deploy instance")
            nova.servers.delete(instance)
            raise
        msg = f"Deploy operation done. Instance created {instance.name}:{instance.id}"
        logger.info(msg)
        return instance_service

    @staticmethod
    def _prepare_creating_args(
        deploy_app: OSNovaImgDeployApp,
        resource_conf: OSResourceConfig,
        nova: NovaClient,
    ) -> dict:
        img_obj = nova.glance.find_image(deploy_app.image_id)
        flavor_obj = nova.flavors.find(name=deploy_app.instance_flavor)
        name = f'{deploy_app.app_name}-{str(uuid.uuid4()).split("-")[0]}'
        server_create_args = {
            "name": name,
            "image": img_obj,
            "flavor": flavor_obj,
            "nics": [{"net-id": resource_conf.os_mgmt_net_id}],
        }
        if deploy_app.availability_zone:
            server_create_args["availability_zone"] = deploy_app.availability_zone
        if deploy_app.affinity_group_id:
            server_create_args["scheduler_hints"] = {
                "group": deploy_app.affinity_group_id
            }
        if deploy_app.auto_udev:
            server_create_args.update({"userdata": _get_udev_rules()})
        return server_create_args

    @classmethod
    def get_with_id(
        cls,
        nova: NovaClient,
        instance_id: str,
        logger: Logger,
    ) -> "NovaService":
        try:
            instance = nova.servers.find(id=instance_id)
        except nova_exceptions.NotFound:
            logger.exception(f"Instance with instance ID {instance_id} Not Found")
            raise
        else:
            return cls(instance, nova, logger)

    @property
    def status(self) -> NovaInstanceStatus:
        return NovaInstanceStatus(self.instance.status)

    def _wait_for_status(
        self,
        status: STATUS,
        delay: int = WAIT_DELAY,
        cancellation_manager: ContextManager = nullcontext(),
    ):
        while self.status not in (status, self.STATUS.ERROR):
            time.sleep(delay)
            with cancellation_manager:
                self.instance.get()
        if self.status is self.STATUS.ERROR:
            raise InstanceErrorStateException(self.instance.fault["message"])

    def power_on(self):
        if self.status is not self.STATUS.ACTIVE:
            self.instance.start()
            self._wait_for_status(self.STATUS.ACTIVE)

    def power_off(self):
        if self.status != self.STATUS.SHUTOFF:
            self.instance.stop()
            self._wait_for_status(self.STATUS.SHUTOFF)

    def attach_interface(self, net_id: str):
        self._nova.servers.interface_attach(
            self.instance, port_id=None, net_id=net_id, fixed_ip=None
        )

    def detach_nic_from_instance(self, port_id: str):
        self._nova.servers.interface_detach(self.instance, port_id)

    def get_instance_image(self) -> Image:
        return self._nova.glance.find_image(self.instance.image["id"])

    def get_instance_flavor(self) -> Flavor:
        return self._nova.flavors.get(self.instance.flavor["id"])

    def terminate(self):
        self._logger.info(f"Deleting instance {self.instance.id}")
        self.instance.delete()


def _get_udev_rules() -> str:
    file_path = Path(__file__).parent / "udev_rules.sh"
    with file_path.open() as f:
        data = f.read()
    return data
