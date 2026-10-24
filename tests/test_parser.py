"""Unit tests for the recursive descent parser."""

import unittest
from static_analyzer.lexer.lexer import Lexer
from static_analyzer.parser.parser import Parser
from static_analyzer.parser.ast_nodes import (
    Program, FunctionDeclaration, VariableDeclaration,
    IfStatement, WhileStatement, ForStatement, ReturnStatement
)


class TestParser(unittest.TestCase):

    def test_function_parsing(self):
        code = "int add(int a, int b) { return a + b; }"
        tokens, _ = Lexer(code).tokenize()
        ast, diags = Parser(tokens).parse()
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(ast.declarations), 1)
        fn = ast.declarations[0]
        self.assertIsInstance(fn, FunctionDeclaration)
        self.assertEqual(fn.name, "add")
        self.assertEqual(len(fn.parameters), 2)
        self.assertEqual(len(fn.body.statements), 1)
        self.assertIsInstance(fn.body.statements[0], ReturnStatement)

    def test_control_flow_parsing(self):
        code = """
        void test() {
            int i = 0;
            while (i < 10) {
                if (i == 5) {
                    break;
                }
                i++;
            }
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, diags = Parser(tokens).parse()
        self.assertEqual(len(diags), 0)
        fn = ast.declarations[0]
        stmts = fn.body.statements
        self.assertIsInstance(stmts[0], VariableDeclaration)
        self.assertIsInstance(stmts[1], WhileStatement)

    def test_top_level_expression_parsing(self):
        code = "int x = 0; ++x; (x = 5);"
        tokens, _ = Lexer(code).tokenize()
        ast, diags = Parser(tokens).parse()
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(ast.declarations), 3)


if __name__ == "__main__":
    unittest.main()
