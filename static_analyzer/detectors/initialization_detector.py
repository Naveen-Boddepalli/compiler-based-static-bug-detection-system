"""Initialization detector checking for uninitialized reads and unused variables."""

from typing import List
from .base import BaseDetector
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..parser.ast_nodes import Program
from ..semantics.symbol_table import SymbolTable, Symbol, SymbolKind
from ..cfg.basic_block import ControlFlowGraph
from ..cfg.data_flow import DataFlowAnalyzer


class InitializationDetector(BaseDetector):
    """Detects variables used without prior initialization and declared variables never used."""

    def run(self, program: Program, symbol_table: SymbolTable, cfgs: List[ControlFlowGraph]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        # 1. Path-sensitive uninitialized variable detection via CFG data-flow
        for cfg in cfgs:
            dfa = DataFlowAnalyzer(cfg, symbol_table)
            dfa_diags = dfa.analyze()
            diagnostics.extend(dfa_diags)

        # 2. Unused variable detection
        for sym in symbol_table.get_all_symbols():
            if sym.kind == SymbolKind.VARIABLE:
                if not sym.is_used:
                    diagnostics.append(Diagnostic(
                        severity=Severity.WARNING,
                        category=DiagnosticCategory.INITIALIZATION,
                        code="INIT-003",
                        message=f"Variable '{sym.name}' is declared but never used",
                        location=sym.declared_location,
                        range=sym.declared_range,
                        suggestion=f"Remove variable '{sym.name}' or use it in the program"
                    ))
            elif sym.kind == SymbolKind.PARAMETER:
                # Warning for unused function parameters (excluding main)
                if not sym.is_used:
                    diagnostics.append(Diagnostic(
                        severity=Severity.INFO,
                        category=DiagnosticCategory.INITIALIZATION,
                        code="INIT-004",
                        message=f"Parameter '{sym.name}' is never used in function body",
                        location=sym.declared_location,
                        range=sym.declared_range,
                        suggestion=f"Consider removing unused parameter '{sym.name}'"
                    ))

        return diagnostics
