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
