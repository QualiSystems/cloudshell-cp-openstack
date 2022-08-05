from __future__ import annotations

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


class PortNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        if id_:
            msg = f"Port with id '{id_}' not found"
        else:
            msg = f"Port with name '{name}' not found"

        super().__init__(msg)


class TrunkNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        if id_:
            msg = f"Trunk with id '{id_}' not found"
        else:
            msg = f"Trunk with name '{name}' not found"

        super().__init__(msg)


class NetworkNotFound(NetworkException):
    def __init__(self, *, id_: str | None = None, name: str | None = None):
        if id_:
            msg = f"Network with id '{id_}' not found"
        else:
            msg = f"Network with name '{name}' not found"

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
