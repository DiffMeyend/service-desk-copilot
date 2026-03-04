"""Core utilities for QF_Wiz.

This module provides centralized exceptions, result types, and field path constants.
"""

from .exceptions import (
    QFWizError,
    ConfigurationError,
    RuntimeLoadError,
    DataError,
    FileLoadError,
    ParseError,
    OperationError,
    CPError,
    CommandError,
)
from .result import Result, Success, Failure, is_success, unwrap_or
from .field_paths import (
    MetaPaths,
    TicketPaths,
    EnvironmentPaths,
    ProblemPaths,
    EvidencePaths,
    BranchesPaths,
    CSSPaths,
    DecisionPaths,
    ConstraintsPaths,
    GuardrailsPaths,
    NotesPaths,
    QuickfixPaths,
    PlanPaths,
    CP,
)

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
