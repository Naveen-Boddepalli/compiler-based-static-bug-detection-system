"""Unit tests for the lexical analyzer."""

import unittest
from static_analyzer.lexer.lexer import Lexer
from static_analyzer.lexer.tokens import TokenType


class TestLexer(unittest.TestCase):

    def test_keywords_and_identifiers(self):
        code = "int x float y char z void bool if else while for return break continue"
        lexer = Lexer(code)
        tokens, diags = lexer.tokenize()
        self.assertEqual(len(diags), 0)
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [
            TokenType.KW_INT, TokenType.IDENTIFIER,
            TokenType.KW_FLOAT, TokenType.IDENTIFIER,
            TokenType.KW_CHAR, TokenType.IDENTIFIER,
            TokenType.KW_VOID, TokenType.KW_BOOL,
            TokenType.KW_IF, TokenType.KW_ELSE,
            TokenType.KW_WHILE, TokenType.KW_FOR,
            TokenType.KW_RETURN, TokenType.KW_BREAK,
            TokenType.KW_CONTINUE
        ]
        self.assertEqual(types, expected)

    def test_numeric_literals(self):
        code = "42 3.14 0x2A"
        lexer = Lexer(code)
        tokens, diags = lexer.tokenize()
        self.assertEqual(len(diags), 0)
        self.assertEqual(tokens[0].value, 42)
        self.assertEqual(tokens[1].value, 3.14)
        self.assertEqual(tokens[2].value, 42)

    def test_operators_and_comments(self):
        code = """
        // Single line comment
        /* Multi
           line */
        x += 5;
        if (a == b && c != d) {}
        """
        lexer = Lexer(code)
        tokens, diags = lexer.tokenize()
        self.assertEqual(len(diags), 0)
        lexemes = [t.lexeme for t in tokens if t.type != TokenType.EOF]
        self.assertIn("+=", lexemes)
        self.assertIn("==", lexemes)
        self.assertIn("&&", lexemes)
        self.assertIn("!=", lexemes)


if __name__ == "__main__":
    unittest.main()
