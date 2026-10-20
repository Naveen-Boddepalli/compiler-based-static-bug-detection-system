"""Unit tests for static analysis bug detectors."""

import unittest
from static_analyzer.pipeline import AnalyzerPipeline


class TestDetectors(unittest.TestCase):

    def setUp(self):
        self.pipeline = AnalyzerPipeline()

    def test_uninitialized_variable_detection(self):
        code = """
        int test() {
            int x;
            return x + 5;
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("INIT-001", codes)

    def test_unused_variable_detection(self):
        code = """
        int test() {
            int unused_num = 42;
            return 0;
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("INIT-003", codes)

    def test_division_by_zero_detection(self):
        code = """
        int test() {
            int a = 10 / 0;
            return a;
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("SAFE-001", codes)

    def test_unreachable_code_detection(self):
        code = """
        int test() {
            return 1;
            int dead_stmt = 2;
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("CFG-001", codes)

    def test_constant_while_zero_loop(self):
        code = """
        void test() {
            while (0) {
                int a = 1;
            }
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("CFG-002", codes)


if __name__ == "__main__":
    unittest.main()
