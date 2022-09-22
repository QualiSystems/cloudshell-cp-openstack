from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands import CreateSecurityGroup


@pytest.fixture()
def api():
    return Mock(name="OS API")


@pytest.fixture()
def inst():
    return Mock(name="Instance")


@pytest.fixture()
def command(rollback_manager, cancellation_context_manager, api, deploy_app, inst):
    return CreateSecurityGroup(
        rollback_manager,
        cancellation_context_manager,
        api,
        deploy_app,
        inst,
    )


def test_create_security_group(command, api, inst):
    command.execute()

    expected_name = f"sg-{inst.name}"
    api.SecurityGroup.create.assert_called_once_with(expected_name)
    sg = api.SecurityGroup.create()
    sg.add_rule.assert_called_once_with(
        cidr="0.0.0.0/0",
        protocol="tcp",
        port_range_min=22,
        port_range_max=22,
        direction="ingress",
    )
    inst.add_security_group.assert_called_once_with(sg)


def test_rollback(command, api, inst):
    sg = Mock(name="Security Group")
    command._sg = sg

    command.rollback()

    inst.remove_security_group.assert_called_once_with(sg)
    sg.remove.assert_called_once_with()


def test_failed_to_add_rules(command, api, inst):
    api.SecurityGroup.create.return_value.add_rule.side_effect = Exception(
        "cannot add rules"
    )

    with pytest.raises(Exception):
        command.execute()

    api.SecurityGroup.create.assert_called_once()
    sg = api.SecurityGroup.create()
    sg.remove_assert_called_once_with()
    inst.add_security_group.assert_not_called()


def test_failed_to_add_to_instance(command, api, inst):
    inst.add_security_group.side_effect = Exception("failed to add")

    with pytest.raises(Exception):
        command.execute()

    api.SecurityGroup.create.assert_called_once()
    sg = api.SecurityGroup.create()
    sg.add_rule.assert_called_once()
    inst.add_security_group.assert_called_once()
    sg.remove_assert_called_once_with()
