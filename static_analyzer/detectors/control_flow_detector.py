"""Control Flow bug detector identifying unreachable code and dead loop conditions."""

from typing import List, Optional
from .base import BaseDetector
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..parser.ast_nodes import (
    Program, ASTNode, IfStatement, WhileStatement, ForStatement,
    IntegerLiteralExpression, BoolLiteralExpression, Expression,
    CompoundStatement, ReturnStatement, BreakStatement
)
from ..semantics.symbol_table import SymbolTable
from ..cfg.basic_block import ControlFlowGraph


def is_constant_falsy(expr: Optional[Expression]) -> bool:
    """Checks if expression is a compile-time constant false/zero."""
    if expr is None:
        return False
    if isinstance(expr, IntegerLiteralExpression) and expr.value == 0:
        return True
    if isinstance(expr, BoolLiteralExpression) and expr.value is False:
        return True
    return False


def is_constant_truthy(expr: Optional[Expression]) -> bool:
    """Checks if expression is a compile-time constant true/non-zero."""
    if expr is None:
        return False
    if isinstance(expr, IntegerLiteralExpression) and expr.value != 0:
        return True
    if isinstance(expr, BoolLiteralExpression) and expr.value is True:
        return True
    return False


def body_has_exit(stmt: ASTNode) -> bool:
    """Checks if statement contains a break or return."""
    if isinstance(stmt, (BreakStatement, ReturnStatement)):
        return True
    if isinstance(stmt, CompoundStatement):
        for s in stmt.statements:
            if body_has_exit(s):
                return True
    if isinstance(stmt, IfStatement):
        then_has = body_has_exit(stmt.then_branch)
        else_has = body_has_exit(stmt.else_branch) if stmt.else_branch else False
        return then_has or else_has
    return False


class ControlFlowDetector(BaseDetector):
    """Detects unreachable code, dead conditions, and infinite loops."""

    def run(self, program: Program, symbol_table: SymbolTable, cfgs: List[ControlFlowGraph]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        # 1. Unreachable blocks detected via CFG reachability
        for cfg in cfgs:
            for b in cfg.blocks:
                if not b.is_reachable and not b.is_exit:
                    if b.instructions:
                        first_inst = b.instructions[0]
                        loc = first_inst.range.start if first_inst.range else SourceLocation(1, 1)
                        diagnostics.append(Diagnostic(
                            severity=Severity.WARNING,
                            category=DiagnosticCategory.CONTROL_FLOW,
                            code="CFG-001",
                            message=f"Unreachable code detected in function '{cfg.function_name}': statement '{first_inst.text}' will never be executed",
                            location=loc,
                            range=first_inst.range,
                            suggestion="Remove or reorder statements preceding unconditional jumps or returns"
                        ))

        # 2. Constant condition inspection via AST
        self._check_ast_conditions(program, diagnostics)
        return diagnostics

    def _check_ast_conditions(self, node: ASTNode, diagnostics: List[Diagnostic]):
        if isinstance(node, WhileStatement):
            if is_constant_falsy(node.condition):
                diagnostics.append(Diagnostic(
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.CONTROL_FLOW,
                    code="CFG-002",
                    message="While loop condition is constant false (0); loop body will never execute",
                    location=node.condition.range.start,
                    range=node.condition.range,
                    suggestion="Remove dead loop or update condition expression"
                ))
            elif is_constant_truthy(node.condition):
                if not body_has_exit(node.body):
                    diagnostics.append(Diagnostic(
                        severity=Severity.WARNING,
                        category=DiagnosticCategory.CONTROL_FLOW,
                        code="CFG-003",
                        message="Potential infinite loop: condition is constant true and body contains no 'break' or 'return'",
                        location=node.condition.range.start,
                        range=node.condition.range,
                        suggestion="Add loop termination logic or 'break' statement"
                    ))

        elif isinstance(node, IfStatement):
            if is_constant_falsy(node.condition):
                diagnostics.append(Diagnostic(
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.CONTROL_FLOW,
                    code="CFG-004",
                    message="If condition is constant false; 'then' branch is dead code",
                    location=node.condition.range.start,
                    range=node.condition.range,
                    suggestion="Remove redundant branch or verify condition expression"
                ))
            elif is_constant_truthy(node.condition) and node.else_branch is not None:
                diagnostics.append(Diagnostic(
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.CONTROL_FLOW,
                    code="CFG-005",
                    message="If condition is constant true; 'else' branch is dead code",
                    location=node.condition.range.start,
                    range=node.condition.range,
                    suggestion="Remove unreachable else branch"
                ))

        # Recurse children
        for attr_name in ("declarations", "statements", "body", "then_branch", "else_branch", "init"):
            if hasattr(node, attr_name):
                val = getattr(node, attr_name)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, ASTNode):
                            self._check_ast_conditions(item, diagnostics)
                elif isinstance(val, ASTNode):
                    self._check_ast_conditions(val, diagnostics)
