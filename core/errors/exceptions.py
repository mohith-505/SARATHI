"""SARATHI exception hierarchy.

Rule: every error SARATHI can raise deliberately should be a subclass of
``SarathiError``. This lets the CLI render friendly messages for expected
failures while still allowing unexpected exceptions to surface.
"""

from __future__ import annotations


class SarathiError(Exception):
    """Base class for all SARATHI-raised errors."""


class ConfigurationError(SarathiError):
    """Configuration is missing, malformed, or contradictory."""


class ModelError(SarathiError):
    """Base class for model/provider related failures."""


class ModelUnavailableError(ModelError):
    """The requested model or provider is unavailable or not installed."""


class ModelResponseError(ModelError):
    """The provider returned a response SARATHI could not interpret."""


class ProviderConnectionError(ModelError):
    """SARATHI could not establish a connection to the provider."""


class ToolError(SarathiError):
    """Base class for tool-related failures."""


class ToolNotFoundError(ToolError):
    """Requested tool name is not registered."""


class ToolPermissionError(ToolError, PermissionError):
    """Tool execution was blocked by the permission system."""


class ToolValidationError(ToolError):
    """Tool arguments failed schema validation."""


class PathAccessError(ToolError, PermissionError):
    """A filesystem path was outside the allowed roots."""
