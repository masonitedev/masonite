from typing import TYPE_CHECKING

from .CoreKernel import CoreKernel

if TYPE_CHECKING:
    from .Application import Application


class Kernel(CoreKernel):
    """The standard framework kernel.

    Extends :class:`CoreKernel` with the full set of built-in craft commands
    and, when running under the test runner, the test response capsule. All
    command and testing imports are loaded lazily so importing this module
    never pulls in the whole command suite.
    """

    def register(self) -> None:
        """Register the standard Masonite features in the project."""
        super().register()
        self.register_commands()
        self.register_testing()

    def register_commands(self) -> None:
        """Add the built-in commands to the command registry."""
        from ..commands import (
            TinkerCommand,
            KeyCommand,
            ServeCommand,
            QueueWorkCommand,
            QueueRetryCommand,
            QueueTableCommand,
            QueueFailedCommand,
            AuthCommand,
            MakePolicyCommand,
            MakeControllerCommand,
            MakeJobCommand,
            MakeRequestCommand,
            MakeMailableCommand,
            MakeFactoryCommand,
            MakeProviderCommand,
            PublishPackageCommand,
            MakeTestCommand,
            DownCommand,
            UpCommand,
            MakeCommandCommand,
            MakeViewCommand,
            MakeMiddlewareCommand,
            PresetCommand,
        )

        self.application.make("commands").add(
            TinkerCommand(),
            KeyCommand(),
            ServeCommand(self.application),
            QueueWorkCommand(self.application),
            QueueRetryCommand(self.application),
            QueueFailedCommand(),
            QueueTableCommand(),
            AuthCommand(self.application),
            MakePolicyCommand(self.application),
            MakeControllerCommand(self.application),
            MakeJobCommand(self.application),
            MakeRequestCommand(self.application),
            MakeMailableCommand(self.application),
            MakeFactoryCommand(self.application),
            MakeProviderCommand(self.application),
            PublishPackageCommand(self.application),
            MakeTestCommand(self.application),
            DownCommand(),
            UpCommand(),
            MakeCommandCommand(self.application),
            MakeViewCommand(self.application),
            MakeMiddlewareCommand(self.application),
            PresetCommand(self.application),
        )

    def register_testing(self) -> None:
        """Bind the test response capsule when running under the test runner.

        The capsule is only needed during tests, so it is registered lazily
        and skipped entirely in production — production boots never import the
        testing helpers.
        """
        if not self.application.is_running_tests():
            return

        from ..tests.HttpTestResponse import HttpTestResponse
        from ..tests.TestResponseCapsule import TestResponseCapsule

        self.application.bind("tests.response", TestResponseCapsule(HttpTestResponse))
