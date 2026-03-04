"""Centralized exception definitions for QF_Wiz.

Exception Hierarchy:
    QFWizError (base)
    +-- ConfigurationError (config/runtime loading issues)
    |   +-- RuntimeLoadError (critical file load failures)
    +-- DataError (data processing issues)
    |   +-- FileLoadError (file read failures, distinguishable from empty)
    |   +-- ParseError (parsing failures)
    +-- OperationError (runtime operation issues)
        +-- CPError (context payload operations)
        +-- CommandError (command parsing/execution)

Usage:
    from core.exceptions import CPError, FileLoadError

    # Raise when a CP operation fails
    raise CPError("Failed to save context payload")

    # Raise when a file cannot be loaded (distinguishes from empty file)
    raise FileLoadError("/path/to/file.yaml", "File not found")
"""

from __future__ import annotations


class QFWizError(Exception):
    """Base exception for all QF_Wiz errors.

    All custom exceptions in QF_Wiz inherit from this class,
    allowing callers to catch all QF_Wiz errors with a single except clause.
    """

    pass


class ConfigurationError(QFWizError):
    """Configuration or runtime loading error.

    Raised when there's an issue with configuration files or
    runtime setup that prevents the system from operating correctly.
    """

    pass


class RuntimeLoadError(ConfigurationError):
    """Critical runtime file failed to load.

    Raised when a required runtime file (YAML/JSON configuration)
    cannot be loaded and the system cannot continue without it.

    Attributes:
        filename: The name of the file that failed to load.
        reason: Why the file failed to load.
    """

    def __init__(self, filename: str, reason: str = ""):
        self.filename = filename
        self.reason = reason
        message = f"Failed to load runtime file '{filename}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class DataError(QFWizError):
    """Data processing error.

    Base class for errors that occur during data processing,
    such as parsing or file loading.
    """

    pass


class FileLoadError(DataError):
    """File could not be loaded.

    This exception distinguishes between "file not found" and "file is empty",
    which is critical for error handling in functions that previously returned
    empty dicts silently.

    Attributes:
        path: The path to the file that failed to load.
        reason: Why the file failed to load (e.g., "not found", "permission denied").
        error_type: A machine-readable error type for programmatic handling.
    """

    def __init__(self, path: str, reason: str = "", error_type: str = "load_error"):
        self.path = path
        self.reason = reason
        self.error_type = error_type
        message = f"Failed to load '{path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ParseError(DataError):
    """Parsing failed for a file or data.

    Raised when the content of a file cannot be parsed (e.g., malformed YAML/JSON).

    Attributes:
        path: The path to the file that failed to parse (if applicable).
        reason: Details about the parsing failure.
    """

    def __init__(self, path: str = "", reason: str = ""):
        self.path = path
        self.reason = reason
        if path:
            message = f"Failed to parse '{path}'"
        else:
            message = "Parse error"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class OperationError(QFWizError):
    """Runtime operation error.

    Base class for errors that occur during runtime operations,
    such as context payload manipulation or command execution.
    """

    pass


class CPError(OperationError):
    """Context Payload operation failed.

    Raised when an operation on the Context Payload fails,
    such as loading, saving, or modifying the payload.
    """

    pass


class CommandError(OperationError):
    """Command parsing or execution failed.

    Raised when a command cannot be parsed or executed,
    such as invalid JSON in LOG_RESULT or unknown commands.
    """

    pass
