class IbikiError(Exception):
    """Base error shown to the user without a technical traceback."""


class ValidationError(IbikiError):
    """Raised when a profile or action is invalid."""


class EngineUnavailable(IbikiError):
    """Raised when an optional Windows input dependency is unavailable."""


class ActionBlocked(IbikiError):
    """Raised when a security setting intentionally blocks an action."""
