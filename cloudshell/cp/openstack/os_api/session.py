from logging import Logger

from keystoneauth1.identity import v3
from keystoneauth1.session import Session

from cloudshell.cp.openstack.resource_config import OSResourceConfig


def get_os_session(resource_config: OSResourceConfig, logger: Logger) -> Session:
    logger.debug("Getting OpenStack Session")
    auth = v3.Password(
        auth_url=resource_config.controller_url,
        username=resource_config.user,
        password=resource_config.password,
        project_name=resource_config.os_project_name,
        user_domain_id=resource_config.os_domain_name,
        project_domain_id=resource_config.os_domain_name,
    )
    return Session(auth=auth, verify=False)
