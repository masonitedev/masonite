from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cleo.application import Application as CommandApplication
    from cleo.commands.command import Command


class CommandCapsule:
    def __init__(self, command_application: "CommandApplication"):
        self.command_application = command_application
        self.commands = []
        self.command_name = []

    def add(self, *commands: "Command") -> "CommandCapsule":
        """Register new commands in the application."""
        for command in commands:
            command_name = command.name
            if command_name in self.command_name:
                continue
            self.command_name.append(command_name)
            self.commands.append(command)
            self.command_application.add(command)
        return self

    def swap(self, command: "Command") -> None:
        """Swap an (existing) command with the given one."""
        command_name = command.name
        # if a command with the same name has been registered remove it
        # (no public API to do this yet)
        self.command_application._commands.pop(command_name, None)
        if command_name in self.command_name:
            self.command_name.remove(command_name)
            self.commands = [c for c in self.commands if c.name != command_name]
        self.add(command)

    def run(self):
        """Run the cleo application."""
        return self.command_application.run()
