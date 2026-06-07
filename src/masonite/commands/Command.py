import re

from cleo.commands.command import Command as BaseCommand
from cleo.helpers import argument, option

from ..utils.console import AddCommandColors

_TOKEN_RE = re.compile(r"\{([^}]+)\}")
_NAME_RE = re.compile(r"[A-Za-z0-9:_\-]+")


class Command(BaseCommand, AddCommandColors):
    """Masonite's base command.

    Commands declare their signature in the class docstring using the
    historical cleo 0.8 block format, which this class translates into a
    cleo 2 definition:

        Description of the command

        command:name
            {argument : Argument description}
            {optional_argument? : Optional argument}
            {--flag : Boolean option}
            {--s|--long : Option with a shortcut}
            {--option=? : Option expecting a value}
            {--option=default : Option with a default value}
    """

    def __init__(self, *args, **kwargs):
        self._configure_from_docstring()
        super().__init__()

    def option(self, key=None):
        value = super().option(key)
        if value is None and key is not None:
            # cleo 0.8 compatibility: an optional-value option passed without
            # a value (e.g. a bare --show) reads as present, hence truthy.
            try:
                given_options = self.io.input._options
            except AttributeError:
                return value
            if key in given_options:
                return True
        return value

    @classmethod
    def _configure_from_docstring(cls):
        # configure each concrete command class once
        if "_docstring_parsed" in cls.__dict__:
            return
        doc = cls.__doc__ or ""

        name, description = cls._parse_name_and_description(doc)
        arguments, options = cls._parse_tokens(doc)

        if name:
            cls.name = name
        if description:
            cls.description = description
        cls.arguments = arguments
        cls.options = options
        cls._docstring_parsed = True

    @staticmethod
    def _parse_name_and_description(doc):
        """The command name is the last text line that looks like a command
        slug; every text line before it forms the description."""
        text_lines = [
            line.strip()
            for line in _TOKEN_RE.sub("", doc).splitlines()
            if line.strip()
        ]

        name = None
        name_index = None
        for index, line in enumerate(text_lines):
            if _NAME_RE.fullmatch(line):
                name = line
                name_index = index

        description_lines = (
            text_lines[:name_index] if name_index is not None else text_lines
        )
        return name, " ".join(description_lines)

    @classmethod
    def _parse_tokens(cls, doc):
        arguments = []
        options = []
        for token in _TOKEN_RE.findall(doc):
            spec, _, token_description = token.strip().partition(":")
            spec = spec.strip()
            token_description = token_description.strip() or None

            if spec.startswith("--"):
                options.append(cls._parse_option(spec, token_description))
            else:
                arguments.append(cls._parse_argument(spec, token_description))
        return arguments, options

    @staticmethod
    def _parse_option(spec, description):
        parts = [part.strip().lstrip("-") for part in spec.split("|")]
        short_name = parts[0] if len(parts) > 1 else None
        long_name = parts[-1]

        flag = True
        multiple = False
        default = None
        if "=" in long_name:
            long_name, _, default = long_name.partition("=")
            flag = False
            if default == "*":
                multiple = True
                default = None
            elif default in ("?", ""):
                default = None

        return option(
            long_name,
            short_name,
            description,
            flag=flag,
            value_required=False,
            multiple=multiple,
            default=default,
        )

    @staticmethod
    def _parse_argument(spec, description):
        optional = False
        multiple = False
        default = None
        if spec.endswith("?"):
            spec = spec[:-1]
            optional = True
        elif spec.endswith("*"):
            spec = spec[:-1]
            optional = True
            multiple = True
        elif "=" in spec:
            spec, _, default = spec.partition("=")
            optional = True

        return argument(
            spec, description, optional=optional, multiple=multiple, default=default
        )
