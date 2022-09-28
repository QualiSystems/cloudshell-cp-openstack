from __future__ import annotations

from contextlib import suppress
from logging import Logger
from threading import Lock
from typing import ClassVar

import attr

from cloudshell.cp.openstack.exceptions import PortNotFound, TrunkNotFound
from cloudshell.cp.openstack.os_api.api import OsApi
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
        return instance.name[:16]

    @staticmethod
    def _get_trunk_suffix(action_id: str) -> str:
        i = action_id.index("_")
        first_part = action_id[:i].rsplit("-", 1)[-1]
        second_part = action_id[i + 1 :].split("-", 1)[0]
        suffix = f"{first_part}_{second_part}"
        return suffix

    @staticmethod
    def _get_trunk_port_name(prefix: str, suffix: str) -> str:
        return f"{prefix}-trunk-port-{suffix}"

    @staticmethod
    def _get_trunk_name(prefix: str, suffix: str) -> str:
        return f"{prefix}-trunk-{suffix}"

    @staticmethod
    def _get_sub_port_name(prefix: str, vlan_network: Network, suffix: str) -> str:
        return f"{prefix}-sub-port-{vlan_network.vlan_id}-{suffix}"

    def connect_trunk(
        self, instance: Instance, vlan_network: Network, action_id: str
    ) -> Interface:
        try:
            iface = self._connect_trunk(instance, vlan_network, action_id)
        except Exception:
            self._logger.exception("Failed to create a trunk")
            self.remove_trunk(instance, vlan_network, action_id)
            raise
        return iface

    def _connect_trunk(
        self, instance: Instance, vlan_network: Network, action_id: str
    ) -> Interface:
        self._logger.info(f"Creating a trunk for the {instance} with {vlan_network}")
        prefix = self._get_name_prefix(instance)
        suffix = self._get_trunk_suffix(action_id)
        trunk_port_name = self._get_trunk_port_name(prefix, suffix)
        trunk_name = self._get_trunk_name(prefix, suffix)
        sub_port_name = self._get_sub_port_name(prefix, vlan_network, suffix)

        trunk_network = self._api.Network.get(self._trunk_network_id)
        trunk_port = self._api.Port.find_or_create(trunk_port_name, trunk_network)
        trunk = self._api.Trunk.find_or_create(trunk_name, trunk_port)
        sub_port = self._api.Port.find_or_create(
            sub_port_name, vlan_network, trunk_port.mac_address
        )
        trunk.add_sub_port(sub_port)

        with self.LOCK:
            iface = instance.attach_port(trunk_port)
        return iface

    def remove_trunk(
        self, instance: Instance, vlan_network: Network, action_id: str
    ) -> None:
        self._logger.info(f"Removing a trunk from the {instance} with {vlan_network}")
        prefix = self._get_name_prefix(instance)
        suffix = self._get_trunk_suffix(action_id)
        trunk_port_name = self._get_trunk_port_name(prefix, suffix)
        trunk_name = self._get_trunk_name(prefix, suffix)
        sub_port_name = self._get_sub_port_name(prefix, vlan_network, suffix)

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
