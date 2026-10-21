"""Lexical analyzer (tokenizer) for C-like language subset."""

from typing import List, Tuple, Optional
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from .tokens import Token, TokenType, KEYWORDS


class Lexer:
    """Converts raw C-like source code into a stream of tokens."""

    def __init__(self, source_text: str, filename: str = "<input>"):
        self.source = source_text
        self.filename = filename
        self.length = len(source_text)
        self.cursor = 0
        self.line = 1
        self.column = 1
        self.diagnostics: List[Diagnostic] = []

    def _peek(self, offset: int = 0) -> str:
        idx = self.cursor + offset
        if idx >= self.length:
            return ""
        return self.source[idx]

    def _advance(self) -> str:
        if self.cursor >= self.length:
            return ""
        ch = self.source[self.cursor]
        self.cursor += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def tokenize(self) -> Tuple[List[Token], List[Diagnostic]]:
        """Scans the entire source code and returns tokens and any syntax diagnostics."""
        tokens: List[Token] = []

        while self.cursor < self.length:
            self._skip_whitespace_and_comments()
            if self.cursor >= self.length:
                break

            token = self._scan_token()
            if token is not None:
                tokens.append(token)

        eof_loc = SourceLocation(self.line, self.column)
        eof_token = Token(
            TokenType.EOF,
            "",
            None,
            SourceRange(eof_loc, eof_loc)
        )
        tokens.append(eof_token)
        return tokens, self.diagnostics

    def _skip_whitespace_and_comments(self):
        while self.cursor < self.length:
            ch = self._peek()
            if ch in (" ", "\t", "\r", "\n"):
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                # Single-line comment
                self._advance() # /
                self._advance() # /
                while self.cursor < self.length and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":
                # Multi-line comment
                start_loc = SourceLocation(self.line, self.column)
                self._advance() # /
                self._advance() # *
                closed = False
                while self.cursor < self.length:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    end_loc = SourceLocation(self.line, self.column)
                    self.diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SYNTAX,
                        code="SYN-001",
                        message="Unterminated multi-line comment",
                        location=start_loc,
                        range=SourceRange(start_loc, end_loc),
                        suggestion="Ensure multi-line comments are terminated with '*/'"
                    ))
            else:
                break

    def _scan_token(self) -> Optional[Token]:
        start_line = self.line
        start_col = self.column
        start_loc = SourceLocation(start_line, start_col)

        ch = self._advance()

        # Identifiers and keywords
        if ch.isalpha() or ch == "_":
            lexeme = ch
            while self._peek().isalnum() or self._peek() == "_":
                lexeme += self._advance()
            end_loc = SourceLocation(self.line, self.column)
            token_type = KEYWORDS.get(lexeme, TokenType.IDENTIFIER)
            value = None
            if token_type == TokenType.BOOL_LITERAL:
                value = (lexeme == "true")
            return Token(token_type, lexeme, value, SourceRange(start_loc, end_loc))

        # Numeric literals
        if ch.isdigit():
            lexeme = ch
            is_float = False
            # Check for hex
            if ch == "0" and (self._peek() == "x" or self._peek() == "X"):
                lexeme += self._advance()
                while self._peek() and self._peek() in "0123456789abcdefABCDEF":
                    lexeme += self._advance()
                end_loc = SourceLocation(self.line, self.column)
                try:
                    val = int(lexeme, 16)
                except ValueError:
                    val = 0
                return Token(TokenType.INT_LITERAL, lexeme, val, SourceRange(start_loc, end_loc))

            while self._peek().isdigit():
                lexeme += self._advance()

            if self._peek() == "." and self._peek(1).isdigit():
                is_float = True
                lexeme += self._advance() # .
                while self._peek().isdigit():
                    lexeme += self._advance()

            end_loc = SourceLocation(self.line, self.column)
            if is_float:
                return Token(TokenType.FLOAT_LITERAL, lexeme, float(lexeme), SourceRange(start_loc, end_loc))
            return Token(TokenType.INT_LITERAL, lexeme, int(lexeme), SourceRange(start_loc, end_loc))

        # String literals
        if ch == '"':
            val_chars = []
            closed = False
            while self.cursor < self.length:
                nxt = self._advance()
                if nxt == '"':
                    closed = True
                    break
                if nxt == "\n":
                    break
                if nxt == "\\":
                    esc = self._advance()
                    if esc == "n":
                        val_chars.append("\n")
                    elif esc == "t":
                        val_chars.append("\t")
                    elif esc == "r":
                        val_chars.append("\r")
                    elif esc == "\\":
                        val_chars.append("\\")
                    elif esc == '"':
                        val_chars.append('"')
                    else:
                        val_chars.append(esc)
                else:
                    val_chars.append(nxt)

            end_loc = SourceLocation(self.line, self.column)
            if not closed:
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SYNTAX,
                    code="SYN-002",
                    message="Unterminated string literal",
                    location=start_loc,
                    range=SourceRange(start_loc, end_loc),
                    suggestion="Add closing double quote '\"'"
                ))
            return Token(TokenType.STRING_LITERAL, "".join(val_chars), "".join(val_chars), SourceRange(start_loc, end_loc))

        # Character literals
        if ch == "'":
            char_val = ""
            if self._peek() == "\\":
                self._advance()
                esc = self._advance()
                esc_map = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", "0": "\0"}
                char_val = esc_map.get(esc, esc)
            elif self._peek() != "'":
                char_val = self._advance()

            closed = self._match("'")
            end_loc = SourceLocation(self.line, self.column)
            if not closed:
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SYNTAX,
                    code="SYN-003",
                    message="Unterminated character literal",
                    location=start_loc,
                    range=SourceRange(start_loc, end_loc),
                    suggestion="Add closing single quote '\''"
                ))
            return Token(TokenType.CHAR_LITERAL, char_val, char_val, SourceRange(start_loc, end_loc))

        # Punctuation and Operators
        token_map = {
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA,
        }
        if ch in token_map:
            end_loc = SourceLocation(self.line, self.column)
            return Token(token_map[ch], ch, None, SourceRange(start_loc, end_loc))

        # Operators with multi-char checks
        if ch == "+":
            if self._match("+"):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.INCREMENT, "++", None, SourceRange(start_loc, end_loc))
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.PLUS_ASSIGN, "+=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.PLUS, "+", None, SourceRange(start_loc, end_loc))

        if ch == "-":
            if self._match("-"):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.DECREMENT, "--", None, SourceRange(start_loc, end_loc))
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.MINUS_ASSIGN, "-=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.MINUS, "-", None, SourceRange(start_loc, end_loc))

        if ch == "*":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.STAR_ASSIGN, "*=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.STAR, "*", None, SourceRange(start_loc, end_loc))

        if ch == "/":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.SLASH_ASSIGN, "/=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.SLASH, "/", None, SourceRange(start_loc, end_loc))

        if ch == "%":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.PERCENT_ASSIGN, "%=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.PERCENT, "%", None, SourceRange(start_loc, end_loc))

        if ch == "=":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.EQ, "==", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.ASSIGN, "=", None, SourceRange(start_loc, end_loc))

        if ch == "!":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.NEQ, "!=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.LOGICAL_NOT, "!", None, SourceRange(start_loc, end_loc))

        if ch == "<":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.LTE, "<=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.LT, "<", None, SourceRange(start_loc, end_loc))

        if ch == ">":
            if self._match("="):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.GTE, ">=", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            return Token(TokenType.GT, ">", None, SourceRange(start_loc, end_loc))

        if ch == "&":
            if self._match("&"):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.LOGICAL_AND, "&&", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SYNTAX,
                code="SYN-004",
                message="Unexpected single '&'; did you mean logical AND '&&'?",
                location=start_loc,
                range=SourceRange(start_loc, end_loc),
                suggestion="Use '&&' for logical conjunction"
            ))
            return None

        if ch == "|":
            if self._match("|"):
                end_loc = SourceLocation(self.line, self.column)
                return Token(TokenType.LOGICAL_OR, "||", None, SourceRange(start_loc, end_loc))
            end_loc = SourceLocation(self.line, self.column)
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SYNTAX,
                code="SYN-005",
                message="Unexpected single '|'; did you mean logical OR '||'?",
                location=start_loc,
                range=SourceRange(start_loc, end_loc),
                suggestion="Use '||' for logical disjunction"
            ))
            return None

        # Unknown character
        end_loc = SourceLocation(self.line, self.column)
        self.diagnostics.append(Diagnostic(
            severity=Severity.ERROR,
            category=DiagnosticCategory.SYNTAX,
            code="SYN-006",
            message=f"Unrecognized character '{ch}'",
            location=start_loc,
            range=SourceRange(start_loc, end_loc),
            suggestion="Remove invalid character"
        ))
        return None
