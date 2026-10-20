#!/usr/bin/env python3
"""Command-line interface for the Compiler-Based Static Code Analysis and Bug Detection System."""

import argparse
import json
import sys
import os

from static_analyzer.pipeline import AnalyzerPipeline
from static_analyzer.common.diagnostic import Severity


def main():
    parser = argparse.ArgumentParser(
        description="Compiler-Based Static Code Analysis and Bug Detection System (C-Like Language Subset)"
    )
    parser.add_argument("file", nargs="?", help="Path to C-like source file to analyze")
    parser.add_argument("--json", action="store_true", help="Output analysis report in JSON format")
    parser.add_argument("--dot", action="store_true", help="Print Graphviz DOT representations for all CFGs")
    parser.add_argument("--check-only", action="store_true", help="Return exit code 1 if errors found, 0 otherwise")
    parser.add_argument("--serve", action="store_true", help="Launch interactive web workbench server")
    parser.add_argument("--port", type=int, default=8000, help="Port for web workbench server (default: 8000)")

    args = parser.parse_args()

    if args.serve:
        from server import run_server
        run_server(port=args.port)
        return 0

    if not args.file:
        parser.print_help()
        return 1

    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        return 1

    with open(args.file, "r", encoding="utf-8") as f:
        source_code = f.read()

    pipeline = AnalyzerPipeline()
    result = pipeline.analyze(source_code, filename=args.file)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif args.dot:
        for cfg in result.cfgs:
            print(f"// CFG for function: {cfg.function_name}")
            print(cfg.dot)
            print()
    else:
        print(result.format_cli())

    if args.check_only:
        error_count = sum(1 for d in result.diagnostics if d.severity == Severity.ERROR)
        return 1 if error_count > 0 else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
