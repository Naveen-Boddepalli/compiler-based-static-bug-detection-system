"""Central static analysis compiler pipeline integrating all passes."""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .common.source_location import SourceFile, SourceLocation, SourceRange
from .common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from .lexer.tokens import Token
from .lexer.lexer import Lexer
from .parser.ast_nodes import Program, FunctionDeclaration, ASTNode
from .parser.parser import Parser
from .semantics.symbol_table import SymbolTable
from .semantics.semantic_analyzer import SemanticAnalyzer
from .cfg.basic_block import ControlFlowGraph
from .cfg.cfg_builder import CFGBuilder
from .cfg.cfg_visualizer import CFGVisualizer
from .detectors.initialization_detector import InitializationDetector
from .detectors.control_flow_detector import ControlFlowDetector
from .detectors.safety_detector import SafetyDetector


@dataclass
class CFGArtifact:
    function_name: str
    cfg: ControlFlowGraph
    dot: str
    svg_light: str
    svg_dark: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "cfg": self.cfg.to_dict(),
            "dot": self.dot,
            "svg_light": self.svg_light,
            "svg_dark": self.svg_dark
        }


@dataclass
class AnalysisMetrics:
    total_lines: int = 0
    total_tokens: int = 0
    total_ast_nodes: int = 0
    total_functions: int = 0
    total_basic_blocks: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "total_tokens": self.total_tokens,
            "total_ast_nodes": self.total_ast_nodes,
            "total_functions": self.total_functions,
            "total_basic_blocks": self.total_basic_blocks,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_info": self.total_info,
            "elapsed_ms": round(self.elapsed_ms, 2)
        }


@dataclass
class AnalysisResult:
    filename: str
    source_file: SourceFile
    tokens: List[Token]
    ast: Program
    symbol_table: SymbolTable
    cfgs: List[CFGArtifact]
    diagnostics: List[Diagnostic]
    metrics: AnalysisMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "metrics": self.metrics.to_dict(),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "tokens": [t.to_dict() for t in self.tokens],
            "ast": self.ast.to_dict() if self.ast else None,
            "symbol_table": self.symbol_table.to_dict() if self.symbol_table else None,
            "cfgs": [c.to_dict() for c in self.cfgs]
        }

    def format_cli(self) -> str:
        """Formats the entire analysis report for CLI or plain text inspection."""
        lines = [
            "=" * 72,
            "STATIC CODE ANALYSIS REPORT",
            f"Target: {self.filename} ({self.metrics.total_lines} lines, {self.metrics.total_tokens} tokens)",
            f"Execution time: {self.metrics.elapsed_ms:.2f} ms",
            f"Summary: {self.metrics.total_errors} errors, {self.metrics.total_warnings} warnings, {self.metrics.total_info} info notes",
            "=" * 72,
            ""
        ]

        if not self.diagnostics:
            lines.append("No defects or warnings detected. All static checks passed.")
        else:
            for d in self.diagnostics:
                lines.append(d.format_cli(self.source_file))
                lines.append("-" * 72)

        return "\n".join(lines)


def count_ast_nodes(node: Optional[ASTNode]) -> int:
    if node is None:
        return 0
    cnt = 1
    for attr in ("declarations", "statements", "body", "then_branch", "else_branch",
                 "init", "condition", "step", "expression", "left", "right", "value",
                 "operand", "arguments", "declarators", "parameters"):
        if hasattr(node, attr):
            v = getattr(node, attr)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, ASTNode):
                        cnt += count_ast_nodes(item)
            elif isinstance(v, ASTNode):
                cnt += count_ast_nodes(v)
    return cnt


class AnalyzerPipeline:
    """Orchestrates lexing, parsing, semantic analysis, CFG construction, and bug detection."""

    def __init__(self):
        self.detectors = [
            InitializationDetector(),
            ControlFlowDetector(),
            SafetyDetector()
        ]

    def analyze(self, source_code: str, filename: str = "<input>") -> AnalysisResult:
        start_time = time.perf_counter()
        source_file = SourceFile(filename, source_code)
        all_diagnostics: List[Diagnostic] = []

        # 1. Lexical Analysis
        lexer = Lexer(source_code, filename)
        tokens, lex_diags = lexer.tokenize()
        all_diagnostics.extend(lex_diags)

        # 2. Syntax Analysis
        parser = Parser(tokens, filename)
        ast, parse_diags = parser.parse()
        all_diagnostics.extend(parse_diags)

        # 3. Semantic Analysis
        sem_analyzer = SemanticAnalyzer(filename)
        symbol_table, sem_diags = sem_analyzer.analyze(ast)
        all_diagnostics.extend(sem_diags)

        # 4. Control Flow Graphs & Data-Flow Analysis
        cfg_artifacts: List[CFGArtifact] = []
        raw_cfgs: List[ControlFlowGraph] = []

        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclaration) and decl.body is not None:
                builder = CFGBuilder(decl)
                cfg = builder.build()
                raw_cfgs.append(cfg)

                viz = CFGVisualizer(cfg)
                artifact = CFGArtifact(
                    function_name=decl.name,
                    cfg=cfg,
                    dot=viz.to_dot(),
                    svg_light=viz.to_svg(is_dark=False),
                    svg_dark=viz.to_svg(is_dark=True)
                )
                cfg_artifacts.append(artifact)

        # 5. Static Analysis Bug Detectors
        for detector in self.detectors:
            det_diags = detector.run(ast, symbol_table, raw_cfgs)
            all_diagnostics.extend(det_diags)

        # 6. Deduplicate and sort diagnostics by line, column, severity
        unique_diags = self._deduplicate_and_sort(all_diagnostics)

        # 7. Metrics
        total_blocks = sum(len(c.cfg.blocks) for c in cfg_artifacts)
        err_count = sum(1 for d in unique_diags if d.severity == Severity.ERROR)
        warn_count = sum(1 for d in unique_diags if d.severity == Severity.WARNING)
        info_count = sum(1 for d in unique_diags if d.severity == Severity.INFO)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metrics = AnalysisMetrics(
            total_lines=source_file.line_count,
            total_tokens=len(tokens),
            total_ast_nodes=count_ast_nodes(ast),
            total_functions=len(cfg_artifacts),
            total_basic_blocks=total_blocks,
            total_errors=err_count,
            total_warnings=warn_count,
            total_info=info_count,
            elapsed_ms=elapsed_ms
        )

        return AnalysisResult(
            filename=filename,
            source_file=source_file,
            tokens=tokens,
            ast=ast,
            symbol_table=symbol_table,
            cfgs=cfg_artifacts,
            diagnostics=unique_diags,
            metrics=metrics
        )

    def _deduplicate_and_sort(self, diagnostics: List[Diagnostic]) -> List[Diagnostic]:
        seen = set()
        result = []
        for d in diagnostics:
            key = (d.severity.value, d.code, d.location.line, d.location.column, d.message)
            if key not in seen:
                seen.add(key)
                result.append(d)

        # Severity rank: ERROR first, then WARNING, then INFO
        sev_rank = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
        result.sort(key=lambda d: (d.location.line, d.location.column, sev_rank.get(d.severity, 3)))
        return result
