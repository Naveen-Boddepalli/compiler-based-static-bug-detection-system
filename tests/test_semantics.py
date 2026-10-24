"""Unit tests for semantic analysis and symbol tables."""

import unittest
from static_analyzer.lexer.lexer import Lexer
from static_analyzer.parser.parser import Parser
from static_analyzer.semantics.semantic_analyzer import SemanticAnalyzer


class TestSemantics(unittest.TestCase):

    def test_undeclared_variable(self):
        code = """
        void main() {
            y = 10;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        sem = SemanticAnalyzer()
        _, diags = sem.analyze(ast)
        codes = [d.code for d in diags]
        self.assertIn("SEM-020", codes)

    def test_redeclared_variable_same_scope(self):
        code = """
        void main() {
            int a = 5;
            int a = 10;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        sem = SemanticAnalyzer()
        _, diags = sem.analyze(ast)
        codes = [d.code for d in diags]
        self.assertIn("SEM-002", codes)

    def test_type_mismatch_assignment(self):
        code = """
        void main() {
            int a = 10;
            void b;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        sem = SemanticAnalyzer()
        _, diags = sem.analyze(ast)
        codes = [d.code for d in diags]
        self.assertIn("SEM-001", codes)

    def test_prototype_mismatch(self):
        code = """
        int foo(int a);
        int foo(float a) {
            return 0;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        sem = SemanticAnalyzer()
        _, diags = sem.analyze(ast)
        codes = [d.code for d in diags]
        self.assertIn("SEM-005", codes)

    def test_missing_return_in_non_void_function(self):
        code = """
        int compute() {
            int a = 1;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        sem = SemanticAnalyzer()
        _, diags = sem.analyze(ast)
        codes = [d.code for d in diags]
        self.assertIn("SEM-012", codes)


if __name__ == "__main__":
    unittest.main()
