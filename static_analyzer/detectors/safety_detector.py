"""Safety and code quality detector for division by zero and hazardous operations."""

from typing import List, Optional, Union, Dict
from .base import BaseDetector
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..parser.ast_nodes import (
    Program, ASTNode, BinaryExpression, IntegerLiteralExpression,
    FloatLiteralExpression, BoolLiteralExpression, UnaryExpression,
    GroupedExpression, AssignmentExpression, IdentifierExpression,
    VariableDeclaration, CompoundStatement, Expression
)
from ..semantics.symbol_table import SymbolTable
from ..cfg.basic_block import ControlFlowGraph


def fold_constant_numeric(expr: Optional[Expression], constants: Optional[Dict[str, Union[int, float]]] = None) -> Optional[Union[int, float]]:
    """Recursively evaluates constant numeric expressions, with optional constant variable substitution."""
    if expr is None:
        return None
    if isinstance(expr, IntegerLiteralExpression):
        return expr.value
    if isinstance(expr, FloatLiteralExpression):
        return expr.value
    if isinstance(expr, BoolLiteralExpression):
        return 1 if expr.value else 0
    if isinstance(expr, IdentifierExpression):
        if constants and expr.name in constants:
            return constants[expr.name]
        return None
    if isinstance(expr, GroupedExpression):
        return fold_constant_numeric(expr.expression, constants)
    if isinstance(expr, UnaryExpression):
        val = fold_constant_numeric(expr.operand, constants)
        if val is not None:
            if expr.operator == "+":
                return +val
            elif expr.operator == "-":
                return -val
            elif expr.operator == "!":
                return 0 if val else 1
        return None
    if isinstance(expr, BinaryExpression):
        left_val = fold_constant_numeric(expr.left, constants)
        right_val = fold_constant_numeric(expr.right, constants)
        if left_val is not None and right_val is not None:
            try:
                if expr.operator == "+":
                    return left_val + right_val
                elif expr.operator == "-":
                    return left_val - right_val
                elif expr.operator == "*":
                    return left_val * right_val
                elif expr.operator == "/":
                    if right_val == 0:
                        return 0  # Flag division by zero
                    if isinstance(left_val, float) or isinstance(right_val, float):
                        return left_val / right_val
                    return int(left_val / right_val)
                elif expr.operator == "%":
                    if right_val == 0:
                        return 0
                    return int(left_val) % int(right_val)
                elif expr.operator == "==":
                    return 1 if left_val == right_val else 0
                elif expr.operator == "!=":
                    return 1 if left_val != right_val else 0
                elif expr.operator == "<":
                    return 1 if left_val < right_val else 0
                elif expr.operator == "<=":
                    return 1 if left_val <= right_val else 0
                elif expr.operator == ">":
                    return 1 if left_val > right_val else 0
                elif expr.operator == ">=":
                    return 1 if left_val >= right_val else 0
                elif expr.operator == "&&":
                    return 1 if (left_val and right_val) else 0
                elif expr.operator == "||":
                    return 1 if (left_val or right_val) else 0
            except Exception:
                return None
    return None


class SafetyDetector(BaseDetector):
    """Detects safety defects such as constant division/modulo by zero and dangerous operations."""

    def run(self, program: Program, symbol_table: SymbolTable, cfgs: List[ControlFlowGraph]) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        constants: Dict[str, Union[int, float]] = {}
        self._check_ast_safety(program, diagnostics, constants)
        return diagnostics

    def _check_ast_safety(self, node: ASTNode, diagnostics: List[Diagnostic], constants: Dict[str, Union[int, float]]):
        if isinstance(node, VariableDeclaration):
            for decl in node.declarators:
                if decl.initializer is not None:
                    # Check initializer for safety first
                    self._check_ast_safety(decl.initializer, diagnostics, constants)
                    val = fold_constant_numeric(decl.initializer, constants)
                    if val is not None:
                        constants[decl.name] = val
                    elif decl.name in constants:
                        del constants[decl.name]
            return

        if isinstance(node, AssignmentExpression):
            self._check_ast_safety(node.value, diagnostics, constants)
            val = fold_constant_numeric(node.value, constants)
            target = node.target.name
            if node.operator == "=":
                if val is not None:
                    constants[target] = val
                elif target in constants:
                    del constants[target]
            elif node.operator == "+=":
                if target in constants and val is not None:
                    constants[target] = constants[target] + val
                elif target in constants:
                    del constants[target]
            elif node.operator == "-=":
                if target in constants and val is not None:
                    constants[target] = constants[target] - val
                elif target in constants:
                    del constants[target]
            elif node.operator == "*=":
                if target in constants and val is not None:
                    constants[target] = constants[target] * val
                elif target in constants:
                    del constants[target]
            elif node.operator == "/=":
                if val is not None and val == 0:
                    diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SAFETY,
                        code="SAFE-001",
                        message="Compound division '/=' by constant zero",
                        location=node.value.range.start,
                        range=node.value.range,
                        suggestion="Ensure divisor is non-zero"
                    ))
                elif target in constants and val is not None and val != 0:
                    constants[target] = int(constants[target] / val)
                elif target in constants:
                    del constants[target]
            elif node.operator == "%=":
                if val is not None and val == 0:
                    diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SAFETY,
                        code="SAFE-002",
                        message="Compound modulo '%=' by constant zero",
                        location=node.value.range.start,
                        range=node.value.range,
                        suggestion="Ensure divisor is non-zero"
                    ))
                elif target in constants and val is not None and val != 0:
                    constants[target] = int(constants[target]) % int(val)
                elif target in constants:
                    del constants[target]
            return

        if isinstance(node, UnaryExpression) and node.operator in ("++", "--"):
            self._check_ast_safety(node.operand, diagnostics, constants)
            if isinstance(node.operand, IdentifierExpression):
                target = node.operand.name
                if target in constants:
                    if node.operator == "++":
                        constants[target] += 1
                    else:
                        constants[target] -= 1
            return

        if isinstance(node, BinaryExpression):
            self._check_ast_safety(node.left, diagnostics, constants)
            self._check_ast_safety(node.right, diagnostics, constants)

            if node.operator in ("/", "/="):
                right_val = fold_constant_numeric(node.right, constants)
                if right_val is not None and right_val == 0:
                    diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SAFETY,
                        code="SAFE-001",
                        message="Division by constant zero will cause runtime crash / undefined behavior",
                        location=node.right.range.start,
                        range=node.right.range,
                        suggestion="Ensure denominator is non-zero"
                    ))
            elif node.operator in ("%", "%="):
                right_val = fold_constant_numeric(node.right, constants)
                if right_val is not None and right_val == 0:
                    diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SAFETY,
                        code="SAFE-002",
                        message="Modulo by constant zero will cause runtime crash / undefined behavior",
                        location=node.right.range.start,
                        range=node.right.range,
                        suggestion="Ensure divisor is non-zero"
                    ))
            return

        if isinstance(node, CompoundStatement):
            local_constants = dict(constants)
            for stmt in node.statements:
                self._check_ast_safety(stmt, diagnostics, local_constants)
            return

        # Recurse children
        for attr_name in ("declarations", "statements", "body", "then_branch", "else_branch",
                          "init", "condition", "step", "expression", "operand", "arguments"):
            if hasattr(node, attr_name):
                val = getattr(node, attr_name)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, ASTNode):
                            self._check_ast_safety(item, diagnostics, constants)
                elif isinstance(val, ASTNode):
                    self._check_ast_safety(val, diagnostics, constants)
