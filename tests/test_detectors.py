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

    def test_global_variable_initialized_no_warning(self):
        code = """
        int g = 10;
        int test() {
            return g;
        }
        """
        res = self.pipeline.analyze(code)
        init_codes = [d.code for d in res.diagnostics if d.code in ("INIT-001", "INIT-002")]
        self.assertEqual(len(init_codes), 0)

    def test_compound_assignment_marks_used(self):
        code = """
        int test() {
            int x = 10;
            x += 5;
            return 0;
        }
        """
        res = self.pipeline.analyze(code)
        unused_codes = [d.code for d in res.diagnostics if d.code == "INIT-003"]
        self.assertEqual(len(unused_codes), 0)

    def test_negative_division_by_zero(self):
        code = """
        int test() {
            int a = 10 / -0;
            return a;
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("SAFE-001", codes)

    def test_grouped_constant_while_loop(self):
        code = """
        void test() {
            while ((0)) {
                int a = 1;
            }
        }
        """
        res = self.pipeline.analyze(code)
        codes = [d.code for d in res.diagnostics]
        self.assertIn("CFG-002", codes)

    def test_for_loop_dead_and_infinite_detection(self):
        dead_code = """
        void test_dead() {
            for (int i = 0; 0; i++) {
                int a = 1;
            }
        }
        """
        res_dead = self.pipeline.analyze(dead_code)
        codes_dead = [d.code for d in res_dead.diagnostics]
        self.assertIn("CFG-002", codes_dead)

        inf_code = """
        void test_inf() {
            for (;;) {
                int a = 1;
            }
        }
        """
        res_inf = self.pipeline.analyze(inf_code)
        codes_inf = [d.code for d in res_inf.diagnostics]
        self.assertIn("CFG-003", codes_inf)


if __name__ == "__main__":
    unittest.main()
