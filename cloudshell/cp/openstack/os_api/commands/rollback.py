from abc import abstractmethod
from logging import Logger

from cloudshell.cp.core.cancellation_manager import CancellationContextManager


class RollbackCommandsManager:
    def __init__(self, logger: Logger):
        self._commands = []
        self._logger = logger

    def register_command(self, command: "RollbackCommand"):
        self._commands.append(command)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            for command in self._commands[::-1]:
                if command.executed:
                    try:
                        self._logger.info(f"Running rollback for command {command}")
                        command.rollback()
                    except Exception:
                        self._logger.warning(
                            f"Unable to perform rollback for command {command}",
                            exc_info=True,
                        )


class RollbackCommand:
    def __init__(
        self,
        rollback_manager: RollbackCommandsManager,
        cancellation_manager: CancellationContextManager,
        *args,
        **kwargs,
    ):
        self._rollback_manager = rollback_manager
        self._cancellation_manager = cancellation_manager
        self.executed = False
        rollback_manager.register_command(self)

    @abstractmethod
    def _execute(self, *args, **kwargs):
        pass

    @abstractmethod
    def rollback(self):
        pass

    def execute(self):
        with self._cancellation_manager:
            command_result = self._execute()
            self.executed = True
            return command_result
