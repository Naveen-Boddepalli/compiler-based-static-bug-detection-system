"""Semantic Analyzer performing type checking, scope binding, and semantic issue detection."""

from typing import List, Optional, Tuple, Dict
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..parser.ast_nodes import (
    ASTNode, Program, VariableDeclaration, FunctionDeclaration,
    CompoundStatement, ExpressionStatement, IfStatement, WhileStatement,
    ForStatement, ReturnStatement, BreakStatement, ContinueStatement,
    Expression, IdentifierExpression, IntegerLiteralExpression,
    FloatLiteralExpression, CharLiteralExpression, StringLiteralExpression,
    BoolLiteralExpression, BinaryExpression, UnaryExpression,
    AssignmentExpression, FunctionCallExpression, GroupedExpression,
    ASTVisitor
)
from .types import (
    CType, IntType, FloatType, CharType, BoolType, VoidType,
    ErrorType, FunctionType, resolve_type_by_name, compute_binary_type
)
from .symbol_table import SymbolTable, Symbol, SymbolKind


class SemanticAnalyzer(ASTVisitor):
    """Walks the AST, binds symbols to scopes, checks types, and detects semantic defects."""

    def __init__(self, filename: str = "<input>"):
        self.filename = filename
        self.symbol_table = SymbolTable()
        self.diagnostics: List[Diagnostic] = []
        self.current_function: Optional[FunctionDeclaration] = None
        self.loop_depth = 0
        self.node_types: Dict[int, CType] = {}

    def analyze(self, program: Program) -> Tuple[SymbolTable, List[Diagnostic]]:
        self.visit_Program(program)
        return self.symbol_table, self.diagnostics

    # -------------------------------------------------------------
    # Program & Declarations
    # -------------------------------------------------------------

    def visit_Program(self, node: Program):
        for decl in node.declarations:
            decl.accept(self)

    def visit_VariableDeclaration(self, node: VariableDeclaration):
        ctype = resolve_type_by_name(node.type_node.name)
        if ctype.is_void():
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-001",
                message="Variable cannot have 'void' type",
                location=node.type_node.range.start,
                range=node.type_node.range,
                suggestion="Use a concrete data type like 'int', 'float', or 'char'"
            ))
            ctype = ErrorType()

        for declarator in node.declarators:
            var_name = declarator.name
            init_expr = declarator.initializer

            # Check for redeclaration in the same scope
            existing = self.symbol_table.lookup_local(var_name)
            if existing is not None:
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-002",
                    message=f"Redeclaration of variable '{var_name}' in the same scope",
                    location=declarator.range.start,
                    range=declarator.range,
                    suggestion=f"Variable '{var_name}' was previously declared at line {existing.declared_location.line}",
                    related_locations=[existing.declared_location]
                ))
            else:
                sym = Symbol(
                    name=var_name,
                    type=ctype,
                    kind=SymbolKind.VARIABLE,
                    declared_location=declarator.range.start,
                    declared_range=declarator.range,
                    scope_id=self.symbol_table.current_scope.scope_id,
                    is_initialized=(init_expr is not None)
                )
                self.symbol_table.define(sym)

            # Analyze initializer if present
            if init_expr is not None:
                init_type = init_expr.accept(self)
                if not isinstance(init_type, ErrorType) and not isinstance(ctype, ErrorType):
                    if not ctype.is_compatible_with(init_type):
                        self.diagnostics.append(Diagnostic(
                            severity=Severity.ERROR,
                            category=DiagnosticCategory.SEMANTIC,
                            code="SEM-003",
                            message=f"Type mismatch in initialization of '{var_name}': cannot assign '{init_type}' to '{ctype}'",
                            location=init_expr.range.start,
                            range=init_expr.range,
                            suggestion=f"Cast value or change type of '{var_name}' to '{init_type}'"
                        ))

    def visit_FunctionDeclaration(self, node: FunctionDeclaration):
        ret_type = resolve_type_by_name(node.return_type.name)
        param_types = [resolve_type_by_name(p.type_node.name) for p in node.parameters]
        fn_type = FunctionType(return_type=ret_type, param_types=param_types)

        existing = self.symbol_table.lookup_local(node.name)
        if existing is not None:
            if not isinstance(existing.type, FunctionType):
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-004",
                    message=f"Identifier '{node.name}' redeclared as a function",
                    location=node.range.start,
                    range=node.range,
                    related_locations=[existing.declared_location]
                ))
            elif node.body is not None and existing.is_initialized:
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-005",
                    message=f"Redefinition of function '{node.name}'",
                    location=node.range.start,
                    range=node.range,
                    suggestion=f"Function was already defined at line {existing.declared_location.line}",
                    related_locations=[existing.declared_location]
                ))
        else:
            sym = Symbol(
                name=node.name,
                type=fn_type,
                kind=SymbolKind.FUNCTION,
                declared_location=node.range.start,
                declared_range=node.range,
                scope_id=self.symbol_table.current_scope.scope_id,
                is_initialized=(node.body is not None)
            )
            self.symbol_table.define(sym)

        if node.body is not None:
            old_fn = self.current_function
            self.current_function = node
            self.symbol_table.enter_scope(f"function {node.name}")

            # Define parameters in function scope
            for p, p_type in zip(node.parameters, param_types):
                if p_type.is_void():
                    self.diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SEMANTIC,
                        code="SEM-006",
                        message=f"Parameter '{p.name}' cannot have 'void' type",
                        location=p.range.start,
                        range=p.range
                    ))
                p_sym = Symbol(
                    name=p.name,
                    type=p_type,
                    kind=SymbolKind.PARAMETER,
                    declared_location=p.range.start,
                    declared_range=p.range,
                    scope_id=self.symbol_table.current_scope.scope_id,
                    is_initialized=True
                )
                if not self.symbol_table.define(p_sym):
                    self.diagnostics.append(Diagnostic(
                        severity=Severity.ERROR,
                        category=DiagnosticCategory.SEMANTIC,
                        code="SEM-007",
                        message=f"Duplicate parameter name '{p.name}' in function '{node.name}'",
                        location=p.range.start,
                        range=p.range
                    ))

            # Traverse body statements directly inside the function's scope
            for stmt in node.body.statements:
                stmt.accept(self)

            self.symbol_table.exit_scope()
            self.current_function = old_fn

    # -------------------------------------------------------------
    # Statements
    # -------------------------------------------------------------

    def visit_CompoundStatement(self, node: CompoundStatement):
        self.symbol_table.enter_scope("block")
        for stmt in node.statements:
            stmt.accept(self)
        self.symbol_table.exit_scope()

    def visit_ExpressionStatement(self, node: ExpressionStatement):
        if node.expression is not None:
            node.expression.accept(self)

    def visit_IfStatement(self, node: IfStatement):
        cond_type = node.condition.accept(self)
        if not isinstance(cond_type, ErrorType) and cond_type.is_void():
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-008",
                message="Cannot use 'void' expression as condition in 'if' statement",
                location=node.condition.range.start,
                range=node.condition.range
            ))
        node.then_branch.accept(self)
        if node.else_branch is not None:
            node.else_branch.accept(self)

    def visit_WhileStatement(self, node: WhileStatement):
        cond_type = node.condition.accept(self)
        if not isinstance(cond_type, ErrorType) and cond_type.is_void():
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-009",
                message="Cannot use 'void' expression as condition in 'while' statement",
                location=node.condition.range.start,
                range=node.condition.range
            ))
        self.loop_depth += 1
        node.body.accept(self)
        self.loop_depth -= 1

    def visit_ForStatement(self, node: ForStatement):
        self.symbol_table.enter_scope("for-loop")
        if node.init is not None:
            node.init.accept(self)
        if node.condition is not None:
            cond_type = node.condition.accept(self)
            if not isinstance(cond_type, ErrorType) and cond_type.is_void():
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-010",
                    message="Cannot use 'void' expression as condition in 'for' statement",
                    location=node.condition.range.start,
                    range=node.condition.range
                ))
        if node.step is not None:
            node.step.accept(self)

        self.loop_depth += 1
        node.body.accept(self)
        self.loop_depth -= 1
        self.symbol_table.exit_scope()

    def visit_ReturnStatement(self, node: ReturnStatement):
        if self.current_function is None:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-011",
                message="'return' statement outside of function",
                location=node.range.start,
                range=node.range
            ))
            return

        expected_ret = resolve_type_by_name(self.current_function.return_type.name)

        if node.expression is None:
            if not expected_ret.is_void():
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-012",
                    message=f"Function '{self.current_function.name}' must return a value of type '{expected_ret}'",
                    location=node.range.start,
                    range=node.range,
                    suggestion=f"Provide a return value of type '{expected_ret}'"
                ))
        else:
            actual_type = node.expression.accept(self)
            if expected_ret.is_void():
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-013",
                    message=f"Void function '{self.current_function.name}' should not return a value",
                    location=node.expression.range.start,
                    range=node.expression.range,
                    suggestion="Remove the return value or change the function return type"
                ))
            elif not isinstance(actual_type, ErrorType) and not expected_ret.is_compatible_with(actual_type):
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-014",
                    message=f"Return type mismatch: expected '{expected_ret}', got '{actual_type}'",
                    location=node.expression.range.start,
                    range=node.expression.range,
                    suggestion=f"Cast return expression to '{expected_ret}'"
                ))

    def visit_BreakStatement(self, node: BreakStatement):
        if self.loop_depth <= 0:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-015",
                message="'break' statement not within a loop",
                location=node.range.start,
                range=node.range
            ))

    def visit_ContinueStatement(self, node: ContinueStatement):
        if self.loop_depth <= 0:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-016",
                message="'continue' statement not within a loop",
                location=node.range.start,
                range=node.range
            ))

    # -------------------------------------------------------------
    # Expressions
    # -------------------------------------------------------------

    def visit_IdentifierExpression(self, node: IdentifierExpression) -> CType:
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-020",
                message=f"Undeclared variable '{node.name}'",
                location=node.range.start,
                range=node.range,
                suggestion=f"Declare '{node.name}' before use with an explicit type"
            ))
            return ErrorType()

        sym.mark_used(node.range.start)
        return sym.type

    def visit_IntegerLiteralExpression(self, node: IntegerLiteralExpression) -> CType:
        return IntType()

    def visit_FloatLiteralExpression(self, node: FloatLiteralExpression) -> CType:
        return FloatType()

    def visit_CharLiteralExpression(self, node: CharLiteralExpression) -> CType:
        return CharType()

    def visit_StringLiteralExpression(self, node: StringLiteralExpression) -> CType:
        return CType() # string

    def visit_BoolLiteralExpression(self, node: BoolLiteralExpression) -> CType:
        return BoolType()

    def visit_GroupedExpression(self, node: GroupedExpression) -> CType:
        return node.expression.accept(self)

    def visit_UnaryExpression(self, node: UnaryExpression) -> CType:
        op_type = node.operand.accept(self)
        if isinstance(op_type, ErrorType):
            return ErrorType()

        if node.operator in ("++", "--"):
            if not isinstance(node.operand, IdentifierExpression):
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-021",
                    message=f"Operand of '{node.operator}' must be a variable",
                    location=node.operand.range.start,
                    range=node.operand.range
                ))
                return ErrorType()
            sym = self.symbol_table.lookup(node.operand.name)
            if sym is not None:
                sym.mark_assigned(node.range.start)
            return op_type

        if node.operator == "!":
            return BoolType()

        if node.operator in ("+", "-"):
            if not op_type.is_numeric():
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-022",
                    message=f"Unary '{node.operator}' requires numeric operand, got '{op_type}'",
                    location=node.range.start,
                    range=node.range
                ))
                return ErrorType()
            return op_type

        return op_type

    def visit_BinaryExpression(self, node: BinaryExpression) -> CType:
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)

        res_type = compute_binary_type(left_type, node.operator, right_type)
        if isinstance(res_type, ErrorType) and not isinstance(left_type, ErrorType) and not isinstance(right_type, ErrorType):
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-023",
                message=f"Invalid operands to binary operator '{node.operator}': '{left_type}' and '{right_type}'",
                location=node.range.start,
                range=node.range,
                suggestion="Ensure both operands have compatible numeric types"
            ))
        return res_type

    def visit_AssignmentExpression(self, node: AssignmentExpression) -> CType:
        val_type = node.value.accept(self)
        target_name = node.target.name
        sym = self.symbol_table.lookup(target_name)

        if sym is None:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-020",
                message=f"Undeclared variable '{target_name}'",
                location=node.target.range.start,
                range=node.target.range,
                suggestion=f"Declare '{target_name}' before assignment"
            ))
            return ErrorType()

        sym.mark_assigned(node.range.start)

        if not isinstance(val_type, ErrorType) and not isinstance(sym.type, ErrorType):
            if not sym.type.is_compatible_with(val_type):
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-024",
                    message=f"Cannot assign value of type '{val_type}' to variable '{target_name}' of type '{sym.type}'",
                    location=node.value.range.start,
                    range=node.value.range,
                    suggestion=f"Cast value to '{sym.type}'"
                ))

        return sym.type

    def visit_FunctionCallExpression(self, node: FunctionCallExpression) -> CType:
        sym = self.symbol_table.lookup(node.callee)
        if sym is None:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-025",
                message=f"Call to undeclared function '{node.callee}'",
                location=node.range.start,
                range=node.range,
                suggestion=f"Declare function '{node.callee}' before calling"
            ))
            return ErrorType()

        sym.mark_used(node.range.start)

        if not isinstance(sym.type, FunctionType):
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-026",
                message=f"Called object '{node.callee}' is not a function",
                location=node.range.start,
                range=node.range
            ))
            return ErrorType()

        fn_type: FunctionType = sym.type
        expected_count = len(fn_type.param_types)
        actual_count = len(node.arguments)

        if expected_count != actual_count:
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SEMANTIC,
                code="SEM-027",
                message=f"Function '{node.callee}' expects {expected_count} arguments, but {actual_count} were provided",
                location=node.range.start,
                range=node.range,
                suggestion=f"Provide exactly {expected_count} arguments"
            ))

        for idx, (arg_expr, expected_param_type) in enumerate(zip(node.arguments, fn_type.param_types)):
            actual_arg_type = arg_expr.accept(self)
            if not isinstance(actual_arg_type, ErrorType) and not expected_param_type.is_compatible_with(actual_arg_type):
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SEMANTIC,
                    code="SEM-028",
                    message=f"Argument {idx + 1} to '{node.callee}' has incompatible type: expected '{expected_param_type}', got '{actual_arg_type}'",
                    location=arg_expr.range.start,
                    range=arg_expr.range
                ))

        return fn_type.return_type
