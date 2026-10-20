"""End-to-end integration tests for the full static analysis system."""

import unittest
from static_analyzer.pipeline import AnalyzerPipeline
from static_analyzer.common.diagnostic import Severity


class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.pipeline = AnalyzerPipeline()

    def test_review1_sample_code(self):
        """Tests the exact Review 1 specification code from the project proposal."""
        code = """
        int main() {
            int x;
            if (x > 10) {
                return 0;
            }
            y = x + 5;
            return 0;
        }
        """
        res = self.pipeline.analyze(code, "review1.c")
        self.assertGreater(len(res.diagnostics), 0)

        # Must report uninitialized variable x and undeclared variable y
        messages = [d.message for d in res.diagnostics]
        codes = [d.code for d in res.diagnostics]

        self.assertIn("SEM-020", codes)
        self.assertIn("INIT-001", codes)

        has_x_uninit = any("x" in m and "initialization" in m for m in messages)
        has_y_undecl = any("y" in m and "Undeclared" in m for m in messages)
        self.assertTrue(has_x_uninit)
        self.assertTrue(has_y_undecl)

    def test_clean_valid_program(self):
        """Tests that a correct, well-formed program reports zero errors or warnings."""
        code = """
        int factorial(int n) {
            int result = 1;
            int i = 1;
            while (i <= n) {
                result = result * i;
                i++;
            }
            return result;
        }

        int main() {
            int ans = factorial(5);
            return ans;
        }
        """
        res = self.pipeline.analyze(code, "factorial.c")
        errors = [d for d in res.diagnostics if d.severity == Severity.ERROR]
        warnings = [d for d in res.diagnostics if d.severity == Severity.WARNING]
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)


if __name__ == "__main__":
    unittest.main()
