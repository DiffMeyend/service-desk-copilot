"""Core utilities for QF_Wiz.

This module provides centralized exceptions, result types, and field path constants.
"""

from .exceptions import (
    CommandError,
    ConfigurationError,
    CPError,
    DataError,
    FileLoadError,
    OperationError,
    ParseError,
    QFWizError,
    RuntimeLoadError,
)
from .field_paths import (
    CP,
    BranchesPaths,
    ConstraintsPaths,
    CSSPaths,
    DecisionPaths,
    EnvironmentPaths,
    EvidencePaths,
    GuardrailsPaths,
    MetaPaths,
    NotesPaths,
    PlanPaths,
    ProblemPaths,
    QuickfixPaths,
    TicketPaths,
)
from .llm import LLMClient, get_client
from .result import Failure, Result, Success, is_success, unwrap_or

__all__ = [
    # Exceptions
    "QFWizError",
    "ConfigurationError",
    "RuntimeLoadError",
    "DataError",
    "FileLoadError",
    "ParseError",
    "OperationError",
    "CPError",
    "CommandError",
    # Result types
    "Result",
    "Success",
    "Failure",
    "is_success",
    "unwrap_or",
    # LLM abstraction
    "LLMClient",
    "get_client",
    # Field paths
    "MetaPaths",
    "TicketPaths",
    "EnvironmentPaths",
    "ProblemPaths",
    "EvidencePaths",
    "BranchesPaths",
    "CSSPaths",
    "DecisionPaths",
    "ConstraintsPaths",
    "GuardrailsPaths",
    "NotesPaths",
    "QuickfixPaths",
    "PlanPaths",
    "CP",
]
