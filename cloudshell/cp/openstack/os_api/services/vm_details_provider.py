from __future__ import annotations

from cloudshell.cp.core.request_actions.models import (
    VmDetailsData,
    VmDetailsNetworkInterface,
    VmDetailsProperty,
)

from cloudshell.cp.openstack.os_api.models import Instance


def create(instance: Instance, management_net_id: str) -> VmDetailsData:
    vm_instance = _get_vm_instance_data(instance)
    vm_network = _get_vm_network_data(instance, management_net_id)
    return VmDetailsData(
        vmInstanceData=vm_instance, vmNetworkData=vm_network, appName=instance.name
    )


def _get_vm_instance_data(instance: Instance) -> list[VmDetailsProperty]:
    flavor = instance.flavor
    return [
        VmDetailsProperty("Image", instance.image.name),
        VmDetailsProperty("Flavor", flavor.name),
        VmDetailsProperty("Availability Zone", instance.available_zone),
        VmDetailsProperty("CPU", f"{flavor.vcpus} vCPU"),
        VmDetailsProperty("Memory", f"{flavor.ram_mb} MB"),
        VmDetailsProperty("Disk Size", f"{flavor.disk_gb} GB"),
    ]


def _get_vm_network_data(
    instance: Instance, mgmt_net_id: str
) -> list[VmDetailsNetworkInterface]:
    network_interfaces = []
    for iface in instance.interfaces:
        private_ip = iface.fixed_ip
        public_ip = iface.floating_ip
        is_primary_and_predefined = mgmt_net_id == iface.network_id

        network_data = [
            VmDetailsProperty("IP", private_ip),
            VmDetailsProperty("MAC Address", iface.mac_address),
            VmDetailsProperty("VLAN Name", iface.network.name, hidden=True),
        ]
        if public_ip:
            network_data.append(VmDetailsProperty("Floating IP", public_ip))

        current_interface = VmDetailsNetworkInterface(
            interfaceId=iface.mac_address,
            networkId=iface.network_id,
            isPrimary=is_primary_and_predefined,
            isPredefined=is_primary_and_predefined,
            networkData=network_data,
            privateIpAddress=private_ip,
            publicIpAddress=public_ip,
        )
        network_interfaces.append(current_interface)
    return sorted(network_interfaces, key=_sort_networks_key(mgmt_net_id))


def _sort_networks_key(mgmt_net_id: str):
    def sort(net_iface: VmDetailsNetworkInterface) -> bool:
        # iface with mgmt network would be first
        return net_iface.networkId != mgmt_net_id

    return sort
