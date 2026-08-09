"""Errors raised while reading Starfield plugin containers."""


class PluginFormatError(Exception):
    """Base class for deterministic plugin-format failures."""


class UnsupportedPluginTypeError(PluginFormatError):
    """Raised when a path is not a supported plugin type."""


class PluginParseError(PluginFormatError):
    """Raised when plugin bytes cannot be parsed safely."""


class UnexpectedRecordError(PluginParseError):
    """Raised when the first record is not TES4."""


class TruncatedDataError(PluginParseError):
    """Raised when input bytes end before a structure is complete."""
