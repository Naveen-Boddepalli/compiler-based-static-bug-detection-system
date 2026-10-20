"""Source location and range tracking for compiler diagnostics."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourceLocation:
    """Represents a specific line and column coordinate within a source file."""
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "column": self.column
        }


@dataclass(frozen=True)
class SourceRange:
    """Represents a contiguous range between a start and end location in source text."""
    start: SourceLocation
    end: SourceLocation

    def __str__(self) -> str:
        return f"{self.start.line}:{self.start.column}-{self.end.line}:{self.end.column}"

    def to_dict(self) -> dict:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict()
        }


class SourceFile:
    """Encapsulates source file content with line lookup capabilities."""

    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.content = content
        self._lines = content.splitlines(keepends=True)

    @property
    def line_count(self) -> int:
        return len(self._lines)

    def get_line(self, line_number: int) -> str:
        """Returns the 1-based line content without trailing newline."""
        if 1 <= line_number <= len(self._lines):
            return self._lines[line_number - 1].rstrip("\r\n")
        return ""

    def get_snippet(self, range_or_loc, context_lines: int = 1) -> str:
        """Extracts a source snippet with surrounding context for diagnostics."""
        if isinstance(range_or_loc, SourceRange):
            start_line = range_or_loc.start.line
            end_line = range_or_loc.end.line
        elif isinstance(range_or_loc, SourceLocation):
            start_line = range_or_loc.line
            end_line = range_or_loc.line
        else:
            return ""

        first_line = max(1, start_line - context_lines)
        last_line = min(len(self._lines), end_line + context_lines)

        result_lines = []
        for ln in range(first_line, last_line + 1):
            line_str = self.get_line(ln)
            marker = ">" if start_line <= ln <= end_line else " "
            result_lines.append(f"{marker} {ln:4d} | {line_str}")
        return "\n".join(result_lines)
