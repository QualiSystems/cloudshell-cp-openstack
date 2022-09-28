from __future__ import annotations

from logging import Logger

from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow
from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionModeEnum,
    ConnectivityActionModel,
)
from cloudshell.shell.flows.connectivity.models.driver_response import (
    ConnectivityActionResult,
)
from cloudshell.shell.flows.connectivity.parse_request_service import (
    AbstractParseConnectivityService,
)

from cloudshell.cp.openstack.exceptions import NetworkNotFound
from cloudshell.cp.openstack.models.connectivity_models import OsConnectivityActionModel
from cloudshell.cp.openstack.os_api.api import OsApi
from cloudshell.cp.openstack.os_api.models import Network
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.services.network_service import QVlanNetwork
from cloudshell.cp.openstack.services.trunk_service import QTrunk


class ConnectivityFlow(AbstractConnectivityFlow):
    def __init__(
        self,
        resource_conf: OSResourceConfig,
        parse_connectivity_request_service: AbstractParseConnectivityService,
        logger: Logger,
        api: OsApi | None = None,
    ):
        super().__init__(parse_connectivity_request_service, logger)
        self._resource_conf = resource_conf
        self._api = api or OsApi.from_config(resource_conf, logger)
        self._q_vlan_network = QVlanNetwork(self._api, resource_conf, logger)
        self._q_trunk = QTrunk(self._api, resource_conf, logger)

    def _set_vlan(self, action: OsConnectivityActionModel) -> ConnectivityActionResult:
        action_id = action.action_id
        vlan_id = int(action.connection_params.vlan_service_attrs.vlan_id)
        vm_uuid = action.custom_action_attrs.vm_uuid
        qnq = action.connection_params.vlan_service_attrs.qnq
        port_mode = action.connection_params.mode
        network_id_or_name = action.connection_params.vlan_service_attrs.virtual_network
        subnet_cidr_data = action.connection_params.vlan_service_attrs.subnet_cidr

        instance = self._api.Instance.get(vm_uuid)
        self._logger.info(f"Start adding VLAN {vlan_id} to the {instance}")

        if network_id_or_name:
            # if network name or id is set, we use it without additional checks
            vlan_network = self._get_existed_network(network_id_or_name)
        else:
            vlan_network = self._q_vlan_network.get_or_create_network(
                vlan_id, qnq, subnet_cidr_data
            )

        try:
            if port_mode is ConnectionModeEnum.TRUNK:
                iface = self._q_trunk.connect_trunk(instance, vlan_network, action_id)
            else:
                try:
                    iface = instance.attach_network(vlan_network)
                except Exception:
                    instance.detach_network(vlan_network)
                    raise
        except Exception:
            vlan_network.remove(raise_in_use=False)
            raise

        msg = f"Setting VLAN {vlan_id} successfully completed"
        return ConnectivityActionResult.success_result_vm(
            action, msg, iface.mac_address
        )

    def _remove_vlan(self, action: ConnectivityActionModel) -> ConnectivityActionResult:
        action_id = action.action_id
        vlan_id = int(action.connection_params.vlan_service_attrs.vlan_id)
        vm_uuid = action.custom_action_attrs.vm_uuid
        port_mode = action.connection_params.mode
        mac_address = action.connector_attrs.interface
        network_id_or_name = action.connection_params.vlan_service_attrs.virtual_network

        instance = self._api.Instance.get(vm_uuid)
        self._logger.info(f"Start removing VLAN {vlan_id} from the {instance}")
        try:
            if network_id_or_name:
                vlan_network = self._get_existed_network(network_id_or_name)
            else:
                vlan_network = self._q_vlan_network.get_network(vlan_id)
        except NetworkNotFound:
            self._logger.debug(f"VLAN {vlan_id} already removed")
        else:
            if port_mode is ConnectionModeEnum.TRUNK:
                self._q_trunk.remove_trunk(instance, vlan_network, action_id)
            else:
                instance.detach_network(vlan_network)

            if not network_id_or_name:  # we don't remove existed network
                vlan_network.remove(raise_in_use=False)

        msg = "Removing VLAN successfully completed"
        return ConnectivityActionResult.success_result_vm(action, msg, mac_address)

    def _get_existed_network(self, name_or_id: str) -> Network:
        try:
            network = self._api.Network.get(name_or_id)
        except NetworkNotFound:
            network = self._api.Network.find_first(name_or_id)
        return network
