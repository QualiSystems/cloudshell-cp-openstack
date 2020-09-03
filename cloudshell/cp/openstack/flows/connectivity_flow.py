from logging import Logger
from threading import Lock

from cloudshell.shell.flows.connectivity.basic_flow import AbstractConnectivityFlow

from cloudshell.cp.openstack.exceptions import NetworkNotFoundException
from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.resource_config import OSResourceConfig


class ConnectivityFlow(AbstractConnectivityFlow):
    IS_VLAN_RANGE_SUPPORTED = False
    IS_MULTI_VLAN_SUPPORTED = False

    def __init__(self, resource_conf: OSResourceConfig, os_api: OSApi, logger: Logger):
        super().__init__(logger)
        self._resource_conf = resource_conf
        self._api = os_api
        self._subnet_lock = Lock()

    def _add_vlan_flow(
        self,
        vlan_range: str,
        port_mode: str,
        full_name: str,
        qnq: bool,
        c_tag: str,
        vm_uid: str,
    ):
        net_dict = self._api.get_or_create_net_with_segmentation_id(int(vlan_range))
        if not net_dict["subnets"]:
            with self._subnet_lock:
                self._api.create_subnet(net_dict["id"])

        try:
            instance = self._api.get_instance(vm_uid)
            self._api.attach_interface_to_instance(instance, net_dict["id"])
        except Exception:
            self._api.remove_network(net_dict["id"])
            raise

    def _remove_vlan_flow(
        self, vlan_range: str, full_name: str, port_mode: str, vm_uid: str
    ):
        try:
            net_dict = self._api.get_net_with_segmentation_id(int(vlan_range))
        except NetworkNotFoundException:
            pass
        else:
            instance = self._api.get_instance(vm_uid)
            port_id = self._api.get_port_id_for_net_name(instance, net_dict["name"])
            self._api.detach_interface_from_instance(instance, port_id)
            with self._subnet_lock:
                self._api.remove_network(net_dict["id"])

    def _remove_all_vlan_flow(self, full_name: str, vm_uid: str):
        instance = self._api.get_instance(vm_uid)
        net_ids = self._api.get_all_net_ids_with_segmentation(instance)
        for net_id in net_ids:
            self._api.detach_interface_from_instance(instance, net_id)
        for net_id in net_ids:
            with self._subnet_lock:
                self._api.remove_network(net_id)
