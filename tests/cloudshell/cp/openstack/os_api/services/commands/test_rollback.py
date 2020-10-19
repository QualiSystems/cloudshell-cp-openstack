from unittest.mock import Mock

import pytest

from cloudshell.cp.openstack.os_api.commands.rollback import RollbackCommand


def test_abs_rollback_command(rollback_manager, cancellation_context_manager):
    class MyRollbackCommand(RollbackCommand):
        def _execute(self, *args, **kwargs):
            return super()._execute(*args, **kwargs)

        def rollback(self):
            return super().rollback()

    command = MyRollbackCommand(rollback_manager, cancellation_context_manager)

    assert command._execute() is None  # do nothing
    assert command.rollback() is None  # do nothing


def test_rollback_commands_manager(rollback_manager, cancellation_context_manager):
    actions = Mock()
    actions.command2_execute.side_effect = ValueError("command2 execute failed")

    class Command1(RollbackCommand):
        def _execute(self, *args, **kwargs):
            return actions.command1_execute()

        def rollback(self):
            return actions.command1_rollback()

    class Command2(RollbackCommand):
        def _execute(self, *args, **kwargs):
            return actions.command2_execute()

        def rollback(self):
            return actions.command2_rollback()

    with pytest.raises(ValueError, match="command2 execute failed"):
        with rollback_manager:
            Command1(rollback_manager, cancellation_context_manager).execute()
            Command2(rollback_manager, cancellation_context_manager).execute()

    actions.command1_execute.assert_called_once_with()
    actions.command2_execute.assert_called_once_with()
    actions.command1_rollback.assert_called_once_with()
    actions.command2_rollback.assert_not_called()


def test_rollback_commands_manager_rollback_failed(
    rollback_manager, cancellation_context_manager
):
    actions = Mock()
    actions.command2_execute.side_effect = ValueError("command2 execute failed")
    actions.command1_rollback.side_effect = ValueError("command1 rollback failed")

    class Command1(RollbackCommand):
        def _execute(self, *args, **kwargs):
            return actions.command1_execute()

        def rollback(self):
            return actions.command1_rollback()

    class Command2(RollbackCommand):
        def _execute(self, *args, **kwargs):
            return actions.command2_execute()

        def rollback(self):
            return actions.command2_rollback()

    with pytest.raises(ValueError, match="command2 execute failed"):
        with rollback_manager:
            Command1(rollback_manager, cancellation_context_manager).execute()
            Command2(rollback_manager, cancellation_context_manager).execute()

    actions.command1_execute.assert_called_once_with()
    actions.command2_execute.assert_called_once_with()
    actions.command1_rollback.assert_called_once_with()
    actions.command2_rollback.assert_not_called()
