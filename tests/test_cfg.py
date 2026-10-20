"""Unit tests for Control Flow Graph and basic blocks."""

import unittest
from static_analyzer.lexer.lexer import Lexer
from static_analyzer.parser.parser import Parser
from static_analyzer.cfg.cfg_builder import CFGBuilder


class TestCFG(unittest.TestCase):

    def test_cfg_construction_with_branching(self):
        code = """
        int max(int a, int b) {
            if (a > b) {
                return a;
            } else {
                return b;
            }
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        fn = ast.declarations[0]
        cfg = CFGBuilder(fn).build()

        self.assertIsNotNone(cfg.entry_block)
        self.assertIsNotNone(cfg.exit_block)
        # Entry, exit, then, else, merge
        self.assertGreaterEqual(len(cfg.blocks), 4)
        self.assertGreaterEqual(len(cfg.edges), 4)

    def test_unreachable_block_detection(self):
        code = """
        void dead() {
            return;
            int x = 10;
        }
        """
        tokens, _ = Lexer(code).tokenize()
        ast, _ = Parser(tokens).parse()
        fn = ast.declarations[0]
        cfg = CFGBuilder(fn).build()

        unreachable = cfg.get_unreachable_blocks()
        self.assertGreaterEqual(len(unreachable), 1)


if __name__ == "__main__":
    unittest.main()
