"""Compiler-Based Static Code Analysis and Bug Detection System."""

from .common.source_location import SourceLocation, SourceRange, SourceFile
from .common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from .lexer.tokens import Token, TokenType
from .lexer.lexer import Lexer
from .parser.ast_nodes import Program, ASTNode
from .parser.parser import Parser
from .semantics.types import CType
from .semantics.symbol_table import SymbolTable, Symbol, Scope
from .semantics.semantic_analyzer import SemanticAnalyzer
from .cfg.basic_block import ControlFlowGraph, BasicBlock, Instruction, CFGEdge
from .cfg.cfg_builder import CFGBuilder
from .cfg.data_flow import DataFlowAnalyzer
from .cfg.cfg_visualizer import CFGVisualizer
from .pipeline import AnalyzerPipeline, AnalysisResult, AnalysisMetrics

__all__ = [
    "SourceLocation", "SourceRange", "SourceFile",
    "Diagnostic", "Severity", "DiagnosticCategory",
    "Token", "TokenType", "Lexer",
    "Program", "ASTNode", "Parser",
    "CType", "SymbolTable", "Symbol", "Scope", "SemanticAnalyzer",
    "ControlFlowGraph", "BasicBlock", "Instruction", "CFGEdge",
    "CFGBuilder", "DataFlowAnalyzer", "CFGVisualizer",
    "AnalyzerPipeline", "AnalysisResult", "AnalysisMetrics"
]
