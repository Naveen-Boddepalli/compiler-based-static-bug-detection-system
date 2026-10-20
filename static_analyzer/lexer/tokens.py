"""Token types and Token structure for C-like language subset."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from ..common.source_location import SourceLocation, SourceRange


class TokenType(Enum):
    # End of file / Error
    EOF = auto()
    ERROR = auto()

    # Identifiers and Literals
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    CHAR_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()

    # Keywords - Types
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_CHAR = auto()
    KW_VOID = auto()
    KW_BOOL = auto()

    # Keywords - Control flow
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_RETURN = auto()
    KW_BREAK = auto()
    KW_CONTINUE = auto()

    # Operators - Arithmetic
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %

    # Operators - Assignment
    ASSIGN = auto()         # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=
    STAR_ASSIGN = auto()    # *=
    SLASH_ASSIGN = auto()   # /=
    PERCENT_ASSIGN = auto() # %=

    # Operators - Comparison
    EQ = auto()             # ==
    NEQ = auto()            # !=
    LT = auto()             # <
    LTE = auto()            # <=
    GT = auto()             # >
    GTE = auto()            # >=

    # Operators - Logical
    LOGICAL_AND = auto()    # &&
    LOGICAL_OR = auto()     # ||
    LOGICAL_NOT = auto()    # !

    # Operators - Increment / Decrement
    INCREMENT = auto()      # ++
    DECREMENT = auto()      # --

    # Punctuation
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,


KEYWORDS = {
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "char": TokenType.KW_CHAR,
    "void": TokenType.KW_VOID,
    "bool": TokenType.KW_BOOL,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "for": TokenType.KW_FOR,
    "return": TokenType.KW_RETURN,
    "break": TokenType.KW_BREAK,
    "continue": TokenType.KW_CONTINUE,
    "true": TokenType.BOOL_LITERAL,
    "false": TokenType.BOOL_LITERAL,
}


@dataclass
class Token:
    """Represents a lexical token with precise source coordinates."""
    type: TokenType
    lexeme: str
    value: Any
    range: SourceRange

    @property
    def start_location(self) -> SourceLocation:
        return self.range.start

    @property
    def line(self) -> int:
        return self.range.start.line

    @property
    def column(self) -> int:
        return self.range.start.column

    def to_dict(self) -> dict:
        return {
            "type": self.type.name,
            "lexeme": self.lexeme,
            "value": str(self.value) if self.value is not None else None,
            "range": self.range.to_dict(),
            "line": self.line,
            "column": self.column
        }

    def __str__(self) -> str:
        return f"Token({self.type.name}, '{self.lexeme}', {self.line}:{self.column})"
