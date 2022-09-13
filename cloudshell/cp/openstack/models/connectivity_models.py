from ipaddress import IPv4Address, IPv4Network
from typing import Optional, Tuple

from pydantic import BaseModel, Field, ValidationError, validator

from cloudshell.shell.flows.connectivity.models.connectivity_model import (
    ConnectionParamsModel,
    ConnectivityActionModel,
    VlanServiceModel,
)

from cloudshell.cp.openstack.exceptions import SubnetCidrFormatError


class SubnetCidrData(BaseModel):
    cidr: IPv4Network
    gateway: Optional[IPv4Address]
    allocation_pool: Optional[Tuple[IPv4Address, IPv4Address]]

    @classmethod
    def parse_str_to_dict(cls, data: str) -> dict:
        try:
            parts = data.split(";")
            cidr = parts.pop(0)
            if "/" not in cidr:
                raise SubnetCidrFormatError

            gateway = allocation_pool = None
            if len(parts) == 2:
                gateway = parts[0]
                first, last = parts[1].split("-")
                allocation_pool = (first, last)
            elif len(parts) == 1:
                if "-" in parts[0]:
                    first, last = parts[0].split("-")
                    allocation_pool = (first, last)
                else:
                    gateway = parts[0]
        except ValueError:
            raise SubnetCidrFormatError

        return {"cidr": cidr, "gateway": gateway, "allocation_pool": allocation_pool}

    @classmethod
    def from_str(cls, data: str) -> "SubnetCidrData":
        return cls(**cls.parse_str_to_dict(data))

    def __init__(self, **kwargs) -> None:
        try:
            super().__init__(**kwargs)
        except ValidationError:
            raise SubnetCidrFormatError


class OsVlanServiceModel(VlanServiceModel):
    subnet_cidr: Optional[SubnetCidrData] = Field(None, alias="Subnet CIDR")

    @validator("subnet_cidr", pre=True)
    def parse_cidr_from_str(cls, v):
        result = None
        if v:
            result = SubnetCidrData.parse_str_to_dict(v)
        return result


class OsConnectionParamsModel(ConnectionParamsModel):
    vlan_service_attrs: OsVlanServiceModel = Field(..., alias="vlanServiceAttributes")


class OsConnectivityActionModel(ConnectivityActionModel):
    connection_params: OsConnectionParamsModel = Field(..., alias="connectionParams")
