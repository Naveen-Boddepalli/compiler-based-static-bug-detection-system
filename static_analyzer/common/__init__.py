"""Common data types and diagnostic structures."""

from .source_location import SourceLocation, SourceRange, SourceFile
from .diagnostic import Diagnostic, Severity, DiagnosticCategory

__all__ = [
    "SourceLocation",
    "SourceRange",
    "SourceFile",
    "Diagnostic",
    "Severity",
    "DiagnosticCategory",
]
