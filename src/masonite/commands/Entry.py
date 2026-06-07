"""Craft Command.

This module is really used for backup only if the masonite CLI cannot import this for you.
This can be used by running "python craft". This module is not ran when the CLI can
successfully import commands for you.
"""

from cleo.application import Application

from .. import __version__
from .InstallCommand import InstallCommand
from .KeyCommand import KeyCommand
from .NewCommand import NewCommand
from .ProjectCommand import ProjectCommand

application = Application("Masonite", __version__)

application.add(NewCommand())
application.add(ProjectCommand())
application.add(KeyCommand())
application.add(InstallCommand())

if __name__ == "__main__":
    application.run()
