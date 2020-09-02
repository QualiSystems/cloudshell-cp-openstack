from typing import List

from novaclient.v2.servers import Server as NovaServer

from cloudshell.cp.core.request_actions.models import (
    VmDetailsData,
    VmDetailsNetworkInterface,
    VmDetailsProperty,
)

from cloudshell.cp.openstack.os_api.api import OSApi
from cloudshell.cp.openstack.utils.instance_helpers import (
    get_floating_ip,
    get_private_ip,
)


def create(instance: NovaServer, api: OSApi, management_vlan_id) -> VmDetailsData:
    instance.get()  # update instance data
    vm_instance = _get_vm_instance_data(instance, api)
    vm_network = _get_vm_network_data(instance, api, management_vlan_id)
    return VmDetailsData(
        vmInstanceData=vm_instance, vmNetworkData=vm_network, appName=instance.name
    )


def _get_vm_instance_data(instance: NovaServer, api: OSApi) -> List[VmDetailsProperty]:
    image = api.get_image_from_instance(instance)
    flavor = api.get_flavor_from_instance(instance)
    available_zone = getattr(instance, "OS-EXT-AZ:availability_zone")
    return [
        VmDetailsProperty("Image", image.name),
        VmDetailsProperty("Flavor", flavor.name),
        VmDetailsProperty("Availability Zone", available_zone),
        VmDetailsProperty("CPU", f"{flavor.vcpus} vCPU"),
        VmDetailsProperty("Memory", f"{flavor.ram} GB"),
        VmDetailsProperty("Disk Size", f"{flavor.disk} GB"),
    ]


def _get_vm_network_data(
    instance: NovaServer, api: OSApi, mgmt_net_id
) -> List[VmDetailsNetworkInterface]:
    network_interfaces = []
    for interface in instance.interface_list():
        net_dict = api.get_network_dict(id=interface.net_id)
        net_name = net_dict["name"]
        private_ip = get_private_ip(instance, net_name)
        is_primary_and_predefined = mgmt_net_id == interface.net_id
        public_ip = get_floating_ip(instance)

        network_data = [
            VmDetailsProperty("IP", private_ip),
            VmDetailsProperty("MAC Address", interface.mac_addr),
            VmDetailsProperty("VLAN Name", net_name, hidden=True),
        ]
        if public_ip:
            network_data.append(VmDetailsProperty("Floating IP", public_ip))

        current_interface = VmDetailsNetworkInterface(
            interfaceId=interface.mac_addr,
            networkId=net_dict["provider:segmentation_id"],
            isPrimary=is_primary_and_predefined,
            isPredefined=is_primary_and_predefined,
            networkData=network_data,
            privateIpAddress=private_ip,
            publicIpAddress=public_ip,
        )
        network_interfaces.append(current_interface)
    return sorted(network_interfaces, key=lambda x: x.networkId)
