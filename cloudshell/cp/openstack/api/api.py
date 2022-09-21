from __future__ import annotations

from logging import Logger

import attr
from glanceclient.client import Client as GlanceClient_base
from glanceclient.v2.client import Client as GlanceClient
from keystoneauth1.identity.v3 import Password as KeyStoneAuth
from keystoneauth1.session import Session as KeyStoneSession
from neutronclient.v2_0.client import Client as NeutronClient
from novaclient.client import Client as NovaClient_base
from novaclient.v2.client import Client as NovaClient

from cloudshell.cp.openstack.os_api.models import Flavor as _Flavor
from cloudshell.cp.openstack.os_api.models import FloatingIp as _FloatingIp
from cloudshell.cp.openstack.os_api.models import Image as _Image
from cloudshell.cp.openstack.os_api.models import Instance as _Instance
from cloudshell.cp.openstack.os_api.models import Interface as _Interface
from cloudshell.cp.openstack.os_api.models import Network as _Network
from cloudshell.cp.openstack.os_api.models import Port as _Port
from cloudshell.cp.openstack.os_api.models import SecurityGroup as _SecurityGroup
from cloudshell.cp.openstack.os_api.models import Subnet as _Subnet
from cloudshell.cp.openstack.os_api.models import Trunk as _Trunk
from cloudshell.cp.openstack.resource_config import OSResourceConfig
from cloudshell.cp.openstack.utils.cached_property import cached_property


@attr.s(auto_attribs=True, str=False)
class OsApi:
    API_VERSION = "2"
    _session: KeyStoneSession
    _logger: Logger

    def __str__(self) -> str:
        return f"OpenStack API '{self._session.auth.auth_url}'"

    @classmethod
    def connect(
        cls,
        controller_url: str,
        user: str,
        password: str,
        project_name: str,
        domain_name: str,
        logger: Logger,
    ) -> OsApi:
        logger.debug("Getting OpenStack Session")
        auth = KeyStoneAuth(
            auth_url=controller_url,
            username=user,
            password=password,
            project_name=project_name,
            user_domain_id=domain_name,
            project_domain_id=domain_name,
        )
        session = KeyStoneSession(auth=auth, verify=False)
        return cls(session, logger)

    @classmethod
    def from_config(cls, conf: OSResourceConfig, logger: Logger) -> OsApi:
        return cls.connect(
            controller_url=conf.controller_url,
            user=conf.user,
            password=conf.password,
            project_name=conf.os_project_name,
            domain_name=conf.os_domain_name,
            logger=logger,
        )

    @cached_property
    def _nova(self) -> NovaClient:
        return NovaClient_base(self.API_VERSION, session=self._session, insecure=True)

    @cached_property
    def _neutron(self) -> NeutronClient:
        return NeutronClient(session=self._session, insecure=True)

    @cached_property
    def _glance(self) -> GlanceClient:
        return GlanceClient_base(self.API_VERSION, session=self._session)

    @cached_property
    def Port(self) -> type[_Port]:
        class Port(_Port):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return Port

    @cached_property
    def Network(self) -> type[_Network]:
        class Network(_Network):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return Network

    @cached_property
    def Subnet(self) -> type[_Subnet]:
        class Subnet(_Subnet):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return Subnet

    @cached_property
    def FloatingIp(self) -> type[_FloatingIp]:
        class FloatingIp(_FloatingIp):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return FloatingIp

    @cached_property
    def SecurityGroup(self) -> type[_SecurityGroup]:
        class SecurityGroup(_SecurityGroup):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return SecurityGroup

    @cached_property
    def Trunk(self) -> type[_Trunk]:
        class Trunk(_Trunk):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return Trunk

    @cached_property
    def Instance(self) -> type[_Instance]:
        class Instance(_Instance):
            api = self
            _nova = self._nova
            _logger = self._logger

        return Instance

    @cached_property
    def Interface(self) -> type[_Interface]:
        class Interface(_Interface):
            api = self
            _neutron = self._neutron
            _logger = self._logger

        return Interface

    @cached_property
    def Image(self) -> type[_Image]:
        class Image(_Image):
            api = self
            _glance = self._glance
            _logger = self._logger

        return Image

    @cached_property
    def Flavor(self) -> type[_Flavor]:
        class Flavor(_Flavor):
            api = self
            _nova = self._nova
            _logger = self._logger

        return Flavor
