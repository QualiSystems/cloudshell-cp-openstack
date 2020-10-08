from __future__ import annotations

from logging import Logger

from keystoneauth1.session import Session as KeyStoneSession
from neutronclient.v2_0.client import Client as NeutronClient
from novaclient.client import Client as NovaClient_base
from novaclient.v2.client import Client as NovaClient
from novaclient.v2.flavors import Flavor
from novaclient.v2.images import Image
from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.cancellation_manager import CancellationContextManager

from cloudshell.cp.openstack.models import OSNovaImgDeployApp
from cloudshell.cp.openstack.models.deploy_app import SecurityGroupRule
from cloudshell.cp.openstack.os_api.services import NeutronService, NovaService
from cloudshell.cp.openstack.os_api.session import get_os_session
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.cached_property import cached_property


class OSApi:
    API_VERSION = "2"
    NET_WITH_SEGMENTATION_PREFIX = "qs_net_segmentation_id_"

    def __init__(self, resource_conf: OSResourceConfig, logger: Logger):
        self._resource_conf = resource_conf
        self._logger = logger

    @cached_property
    def _os_session(self) -> KeyStoneSession:
        return get_os_session(self._resource_conf, self._logger)

    @cached_property
    def _nova(self) -> NovaClient:
        return NovaClient_base(
            self.API_VERSION, session=self._os_session, insecure=True
        )

    @cached_property
    def _neutron(self) -> NeutronClient:
        return NeutronClient(session=self._os_session, insecure=True)

    @cached_property
    def _neutron_service(self) -> NeutronService:
        return NeutronService(self._neutron, self._logger)

    def _get_nova_service(self, instance: NovaServer) -> NovaService:
        return NovaService(instance, self._nova, self._logger)

    def create_instance(
        self,
        deploy_app: OSNovaImgDeployApp,
        cancellation_manager: CancellationContextManager,
    ) -> NovaServer:
        instance_service = NovaService.create_instance(
            self._nova,
            self._resource_conf,
            deploy_app,
            cancellation_manager,
            self._logger,
        )
        return instance_service.instance

    def get_network_dict(self, **kwargs) -> dict:
        return self._neutron_service.get_network(**kwargs)

    def get_network_name(self, net_id: str) -> str:
        return self._neutron_service.get_network_name(net_id)

    def get_network_id_for_subnet_id(self, subnet_id: str) -> str:
        return self._neutron_service.get_subnet(id=subnet_id)["network_id"]

    def create_floating_ip(self, subnet_id: str, port_id: str) -> str:
        return self._neutron_service.create_floating_ip(subnet_id, port_id)

    def delete_floating_ip(self, ip: str):
        return self._neutron_service.delete_floating_ip(ip)

    def get_image_from_instance(self, instance: NovaServer) -> Image:
        return self._get_nova_service(instance).get_instance_image()

    def get_flavor_from_instance(self, instance: NovaServer) -> Flavor:
        return self._get_nova_service(instance).get_instance_flavor()

    def terminate_instance(self, instance: NovaServer):
        self._get_nova_service(instance).terminate()

    def get_instance(self, instance_id: str) -> NovaServer:
        return NovaService.get_with_id(self._nova, instance_id, self._logger).instance

    def power_on_instance(self, instance: NovaServer):
        return self._get_nova_service(instance).power_on()

    def power_off_instance(self, instance: NovaServer):
        return self._get_nova_service(instance).power_off()

    def create_network(self, net_data: dict) -> dict:
        return self._neutron_service.create_network(net_data)

    def remove_network(self, net_id: str):
        return self._neutron_service.remove_network(net_id)

    def get_or_create_net_with_segmentation_id(self, id_: int) -> dict:
        return self._neutron_service.get_or_create_net_with_segmentation_id(
            id_, self._resource_conf, self.NET_WITH_SEGMENTATION_PREFIX
        )

    def get_net_with_segmentation_id(self, id_: int) -> dict:
        return self._neutron_service.get_net_with_segmentation(id_)

    def get_port_id_for_net_name(self, instance: NovaServer, net_name: str) -> str:
        for interface in instance.interface_list():
            if self.get_network_name(interface.net_id) == net_name:
                return interface.port_id

    def get_all_net_ids_with_segmentation(self, instance: NovaServer):
        net_names = [
            name
            for name in instance.networks.keys()
            if name.startswith(self.NET_WITH_SEGMENTATION_PREFIX)
        ]
        return [self.get_network_dict(name=name)["id"] for name in net_names]

    def create_subnet(self, net_id: str):
        return self._neutron_service.create_subnet(
            net_id, self._resource_conf.os_reserved_networks
        )

    def attach_interface_to_instance(self, instance: NovaServer, net_id: str):
        self._get_nova_service(instance).attach_interface(net_id)

    def detach_interface_from_instance(self, instance: NovaServer, net_id: str):
        self._get_nova_service(instance).detach_nic_from_instance(net_id)

    def create_security_group_for_instance(
        self, instance: NovaServer, rules: list[SecurityGroupRule]
    ) -> str:
        sg_id = self._neutron_service.create_security_group(f"sg-{instance.name}")
        try:
            for rule in rules:
                self._neutron_service.create_security_group_rule(
                    sg_id,
                    rule.cidr,
                    rule.port_range_min,
                    rule.port_range_max,
                    rule.protocol,
                )
            instance.add_security_group(sg_id)
        except Exception:
            self._neutron_service.delete_security_group(sg_id)
            raise
        return sg_id

    def delete_security_group_for_instance(self, instance: NovaServer):
        security_groups = instance.list_security_group()
        for sg in security_groups:
            if sg.name == f"sg-{instance.name}":
                instance.remove_security_group(sg.id)
                self._neutron_service.delete_security_group(sg.id)
