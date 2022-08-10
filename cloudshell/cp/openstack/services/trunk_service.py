from __future__ import annotations

from contextlib import suppress
from logging import Logger
from threading import Lock
from typing import ClassVar

import attr

from cloudshell.cp.openstack.api.api import OsApi
from cloudshell.cp.openstack.exceptions import PortNotFound, TrunkNotFound
from cloudshell.cp.openstack.os_api.models import Instance, Interface, Network
from cloudshell.cp.openstack.resource_config import OSResourceConfig


@attr.s(auto_attribs=True)
class QTrunk:
    LOCK: ClassVar[Lock] = Lock()
    _api: OsApi
    _resource_conf: OSResourceConfig
    _logger: Logger

    @property
    def _trunk_network_id(self) -> str:
        return self._resource_conf.os_trunk_net_id or self._resource_conf.os_mgmt_net_id

    @staticmethod
    def _get_name_prefix(instance: Instance) -> str:
        return instance.name[:60]

    def _get_trunk_port_name(self, instance: Instance) -> str:
        return f"{self._get_name_prefix(instance)}-trunk-port"

    def _get_trunk_name(self, instance: Instance) -> str:
        return f"{self._get_name_prefix(instance)}-trunk"

    def _get_sub_port_name(self, instance: Instance, vlan_network: Network) -> str:
        prefix = self._get_name_prefix(instance)
        return f"{prefix}-sub-port-{vlan_network.vlan_id}"

    def connect_trunk(self, instance: Instance, vlan_network: Network) -> Interface:
        try:
            iface = self._connect_trunk(instance, vlan_network)
        except Exception:
            self._logger.exception("Failed to create a trunk")
            self.remove_trunk(instance, vlan_network)
            raise
        return iface

    def _connect_trunk(self, instance: Instance, vlan_network: Network) -> Interface:
        self._logger.info(f"Creating a trunk for the {instance} with {vlan_network}")
        trunk_network = self._api.Network.get(self._trunk_network_id)
        trunk_port_name = self._get_trunk_port_name(instance)
        trunk_name = self._get_trunk_name(instance)
        sub_port_name = self._get_sub_port_name(instance, vlan_network)

        trunk_port = self._api.Port.find_or_create(trunk_port_name, trunk_network)
        trunk = self._api.Trunk.find_or_create(trunk_name, trunk_port)
        sub_port = self._api.Port.find_or_create(
            sub_port_name, vlan_network, trunk_port.mac_address
        )
        trunk.add_sub_port(sub_port)

        with self.LOCK:
            iface = instance.attach_port(trunk_port)
        return iface

    def remove_trunk(self, instance: Instance, vlan_network: Network) -> None:
        self._logger.info(f"Removing a trunk from the {instance} with {vlan_network}")
        trunk_port_name = self._get_trunk_port_name(instance)
        trunk_name = self._get_trunk_name(instance)
        sub_port_name = self._get_sub_port_name(instance, vlan_network)

        try:
            trunk = self._api.Trunk.find_first(trunk_name)
        except TrunkNotFound:
            with suppress(PortNotFound):
                self._api.Port.find_first(sub_port_name).remove()
            with suppress(PortNotFound):
                self._api.Port.find_first(trunk_port_name).remove()
        else:
            try:
                sub_port = self._api.Port.find_first(sub_port_name)
            except PortNotFound:
                pass
            else:
                trunk.remove_sub_port(sub_port)
                sub_port.remove()

            with suppress(TrunkNotFound, PortNotFound):
                if not trunk.sub_ports_ids:
                    trunk.remove()
                    trunk.port.remove()
                else:
                    instance.detach_port(trunk.port)
