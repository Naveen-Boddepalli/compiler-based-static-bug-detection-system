"""Compiler diagnostic representations for errors, warnings, and static analysis findings."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from .source_location import SourceLocation, SourceRange


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class DiagnosticCategory(Enum):
    SYNTAX = "SYNTAX"
    SEMANTIC = "SEMANTIC"
    INITIALIZATION = "INITIALIZATION"
    CONTROL_FLOW = "CONTROL_FLOW"
    SAFETY = "SAFETY"


@dataclass
class Diagnostic:
    """Represents a single static analysis diagnostic finding."""
    severity: Severity
    category: DiagnosticCategory
    code: str
    message: str
    location: SourceLocation
    range: Optional[SourceRange] = None
    suggestion: Optional[str] = None
    related_locations: Optional[List[SourceLocation]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "location": self.location.to_dict(),
            "range": self.range.to_dict() if self.range else None,
            "suggestion": self.suggestion,
            "related_locations": [loc.to_dict() for loc in (self.related_locations or [])]
        }

    def format_cli(self, source_file=None) -> str:
        """Formats diagnostic for terminal or plain text reports."""
        loc_str = f"{self.location.line}:{self.location.column}"
        header = f"[{self.severity.value}] [{self.code}] {loc_str}: {self.message}"
        lines = [header]
        if self.suggestion:
            lines.append(f"    Suggestion: {self.suggestion}")
        if source_file:
            snippet = source_file.get_snippet(self.range or self.location)
            if snippet:
                lines.append(snippet)
        return "\n".join(lines)
