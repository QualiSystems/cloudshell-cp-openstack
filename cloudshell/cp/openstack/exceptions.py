from typing import Iterable


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


class FreeSubnetIsNotFoundException(NetworkException):
    """Free subnet isn't found exception."""


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


class IfaceWithNetworkIdNotFound(OSBaseException):
    def __init__(self, instance, net_id):
        self.instance = instance
        self.net_id = net_id
        super().__init__(
            f"Not found an interface with network id '{net_id}' in the "
            f"instance {instance}"
        )
