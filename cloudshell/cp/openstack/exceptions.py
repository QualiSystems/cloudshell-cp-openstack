from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from cloudshell.cp.openstack.os_api.models import Instance, Network, Port


class OSBaseException(Exception):
    """Base OpenStack exception."""


class InstanceErrorStateException(OSBaseException):
    """This exception is raised when instance state is ERROR."""


class NetworkException(OSBaseException):
    """Network exception."""


class NetworkNotFoundException(NetworkException):
    """Network not found exception."""


class SubnetNotFoundException(NetworkException):
    """Subnet not found exception."""


class FreeSubnetIsNotFound(NetworkException):
    def __init__(self):
        super().__init__("All Subnets Exhausted")


class InstanceNotFound(OSBaseException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        assert id_ or name
        if id_:
            msg = f"Instance with id '{id_}' not found"
        else:
            msg = f"Instance with name '{name}' not found"

        super().__init__(msg)


class PortNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        assert id_ or name
        if id_:
            msg = f"Port with id '{id_}' not found"
        else:
            msg = f"Port with name '{name}' not found"

        super().__init__(msg)


class PortIsNotGone(NetworkException):
    def __init__(self, port: Port):
        super().__init__(f"The {port} is not gone")


class PortIsNotAttached(NetworkException):
    def __init__(self, port: Port, instance: Instance):
        super().__init__(f"The {port} is not attached to the {instance}")


class TrunkNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        assert id_ or name
        if id_:
            msg = f"Trunk with id '{id_}' not found"
        else:
            msg = f"Trunk with name '{name}' not found"

        super().__init__(msg)


class NetworkNotFound(NetworkException):
    def __init__(
        self,
        *,
        id_: str | None = None,
        name: str | None = None,
        vlan_id: int | None = None,
    ):
        assert id_ or name or vlan_id
        if id_:
            msg = f"Network with id '{id_}' not found"
        elif name:
            msg = f"Network with name '{name}' not found"
        else:
            msg = f"Network with VLAN ID {vlan_id} not found"

        super().__init__(msg)


class NetworkInUse(NetworkException):
    def __init__(self, network: Network):
        super().__init__(f"{network} in use")


class SubnetNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        assert id_ or name
        if id_:
            msg = f"Subnet with id '{id_}' not found"
        else:
            msg = f"Subnet with name '{name}' not found"

        super().__init__(msg)


class NotSupportedConsoleType(OSBaseException):
    """Console type is not supported."""

    def __init__(self, console_type: str, supported_types: Iterable[str]):
        self._console_type = console_type
        self._supported_types = supported_types

    def __str__(self):
        return (
            f"{self._console_type} is not supported. "
            f"You have to use {list(self._supported_types)}"
        )
