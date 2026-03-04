"""Result type for operations that can fail.

Provides explicit success/failure handling without exceptions for
non-critical operations where graceful degradation is acceptable.

This is useful for functions that previously returned empty dicts on error,
making it impossible to distinguish between "error" and "empty data".

Usage:
    from core.result import Result, Success, Failure, is_success, unwrap_or

    def load_optional_config(path: Path) -> Result[Dict[str, Any]]:
        try:
            data = yaml.safe_load(path.read_text())
            return Success(data if isinstance(data, dict) else {})
        except FileNotFoundError:
            return Failure("File not found", error_type="not_found")
        except yaml.YAMLError as e:
            return Failure(f"YAML parse error: {e}", error_type="parse_error")

    # Using the result
    result = load_optional_config(config_path)
    if is_success(result):
        config = result.value
    else:
        print(f"Warning: {result.error}")
        config = {}

    # Or with default value
    config = unwrap_or(result, {})
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union

T = TypeVar("T")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful operation result.

    Attributes:
        value: The successful result value.
    """

    value: T

    def __bool__(self) -> bool:
        """Success is always truthy."""
        return True


@dataclass(frozen=True)
class Failure:
    """Represents a failed operation result.

    Attributes:
        error: Human-readable error message.
        error_type: Machine-readable error type for programmatic handling.
    """

    error: str
    error_type: str = "unknown"

    def __bool__(self) -> bool:
        """Failure is always falsy."""
        return False


# Result is either Success[T] or Failure
Result = Union[Success[T], Failure]


def is_success(result: Result[Any]) -> bool:
    """Check if a result is successful.

    Args:
        result: The result to check.

    Returns:
        True if the result is a Success, False if it's a Failure.
    """
    return isinstance(result, Success)


def is_failure(result: Result[Any]) -> bool:
    """Check if a result is a failure.

    Args:
        result: The result to check.

    Returns:
        True if the result is a Failure, False if it's a Success.
    """
    return isinstance(result, Failure)


def unwrap_or(result: Result[T], default: T) -> T:
    """Get value from result or return default on failure.

    This is useful for graceful degradation where you want to continue
    with a default value if the operation failed.

    Args:
        result: The result to unwrap.
        default: The default value to return if result is a Failure.

    Returns:
        The success value if result is Success, otherwise the default.
    """
    if isinstance(result, Success):
        return result.value
    return default


def unwrap(result: Result[T]) -> T:
    """Get value from result, raising ValueError on failure.

    Use this when you expect the operation to succeed and want
    to fail fast if it doesn't.

    Args:
        result: The result to unwrap.

    Returns:
        The success value.

    Raises:
        ValueError: If result is a Failure.
    """
    if isinstance(result, Success):
        return result.value
    raise ValueError(f"Tried to unwrap a Failure: {result.error}")
