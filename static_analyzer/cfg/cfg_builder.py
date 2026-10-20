"""CFG Builder constructing basic blocks and control flow edges from AST."""

from typing import List, Optional, Set, Tuple
from ..common.source_location import SourceRange
from ..parser.ast_nodes import (
    ASTNode, FunctionDeclaration, CompoundStatement,
    VariableDeclaration, ExpressionStatement, IfStatement,
    WhileStatement, ForStatement, ReturnStatement, BreakStatement,
    ContinueStatement, Expression, IdentifierExpression,
    BinaryExpression, UnaryExpression, AssignmentExpression,
    FunctionCallExpression, GroupedExpression, IntegerLiteralExpression,
    FloatLiteralExpression, CharLiteralExpression, StringLiteralExpression,
    BoolLiteralExpression
)
from .basic_block import (
    ControlFlowGraph, BasicBlock, Instruction, InstructionKind,
    CFGEdge, EdgeKind
)


def extract_used_vars(expr: Optional[Expression]) -> Set[str]:
    """Recursively collects variable names read in an expression."""
    if expr is None:
        return set()
    used = set()
    if isinstance(expr, IdentifierExpression):
        used.add(expr.name)
    elif isinstance(expr, BinaryExpression):
        used.update(extract_used_vars(expr.left))
        used.update(extract_used_vars(expr.right))
    elif isinstance(expr, UnaryExpression):
        used.update(extract_used_vars(expr.operand))
    elif isinstance(expr, AssignmentExpression):
        # The right hand side is read
        used.update(extract_used_vars(expr.value))
        # If compound assignment (+=, etc.), the target is also read first!
        if expr.operator != "=":
            used.add(expr.target.name)
    elif isinstance(expr, FunctionCallExpression):
        for arg in expr.arguments:
            used.update(extract_used_vars(arg))
    elif isinstance(expr, GroupedExpression):
        used.update(extract_used_vars(expr.expression))
    return used


def stringify_expr(expr: Optional[Expression]) -> str:
    """Produces a clean textual representation of an expression for block instructions."""
    if expr is None:
        return ""
    if isinstance(expr, IdentifierExpression):
        return expr.name
    if isinstance(expr, IntegerLiteralExpression):
        return str(expr.value)
    if isinstance(expr, FloatLiteralExpression):
        return str(expr.value)
    if isinstance(expr, CharLiteralExpression):
        return f"'{expr.value}'"
    if isinstance(expr, StringLiteralExpression):
        return f'"{expr.value}"'
    if isinstance(expr, BoolLiteralExpression):
        return "true" if expr.value else "false"
    if isinstance(expr, BinaryExpression):
        return f"{stringify_expr(expr.left)} {expr.operator} {stringify_expr(expr.right)}"
    if isinstance(expr, UnaryExpression):
        if expr.is_prefix:
            return f"{expr.operator}{stringify_expr(expr.operand)}"
        return f"{stringify_expr(expr.operand)}{expr.operator}"
    if isinstance(expr, AssignmentExpression):
        return f"{expr.target.name} {expr.operator} {stringify_expr(expr.value)}"
    if isinstance(expr, FunctionCallExpression):
        args_str = ", ".join(stringify_expr(a) for a in expr.arguments)
        return f"{expr.callee}({args_str})"
    if isinstance(expr, GroupedExpression):
        return f"({stringify_expr(expr.expression)})"
    return "<expr>"


class CFGBuilder:
    """Builds a Control Flow Graph for a function definition."""

    def __init__(self, fn_decl: FunctionDeclaration):
        self.fn_decl = fn_decl
        self.cfg = ControlFlowGraph(function_name=fn_decl.name)
        self.cfg.scope = fn_decl.scope
        self.block_counter = 0

        # Loop stack for break and continue targeting: (continue_target_block, break_target_block)
        self.loop_stack: List[Tuple[BasicBlock, BasicBlock]] = []

    def _new_block(self, label_prefix: str = "B") -> BasicBlock:
        b = BasicBlock(self.block_counter, f"{label_prefix}{self.block_counter}")
        self.block_counter += 1
        self.cfg.add_block(b)
        return b

    def build(self) -> ControlFlowGraph:
        # Create Entry and Exit blocks
        entry = self._new_block("Entry")
        entry.is_entry = True
        self.cfg.entry_block = entry

        exit_block = self._new_block("Exit")
        exit_block.is_exit = True
        self.cfg.exit_block = exit_block

        # Record parameter declarations in entry block
        for p in self.fn_decl.parameters:
            entry.add_instruction(Instruction(
                kind=InstructionKind.DECLARATION,
                text=f"param {p.type_node.name} {p.name}",
                ast_node=p,
                range=p.range,
                defined_vars={p.name},
                used_vars=set()
            ))

        current_block = entry
        if self.fn_decl.body is not None:
            current_block = self._build_compound_statement(self.fn_decl.body, current_block)

        # If current_block still has open fallthrough, link to exit
        if current_block is not None:
            self.cfg.add_edge(current_block, exit_block, EdgeKind.FALLTHROUGH)

        self.cfg.compute_reachability()
        return self.cfg

    def _build_compound_statement(self, stmt: CompoundStatement, current_block: Optional[BasicBlock]) -> Optional[BasicBlock]:
        for s in stmt.statements:
            if current_block is None:
                # Unreachable dead code block
                current_block = self._new_block("dead_code")
                current_block.is_reachable = False

            current_block = self._build_statement(s, current_block)
        return current_block

    def _build_statement(self, stmt: ASTNode, current_block: BasicBlock) -> Optional[BasicBlock]:
        if isinstance(stmt, CompoundStatement):
            return self._build_compound_statement(stmt, current_block)

        if isinstance(stmt, VariableDeclaration):
            for decl in stmt.declarators:
                text = f"{stmt.type_node.name} {decl.name}"
                defined = set()
                used = set()
                if decl.initializer is not None:
                    text += f" = {stringify_expr(decl.initializer)}"
                    used = extract_used_vars(decl.initializer)
                    defined.add(decl.name)

                current_block.add_instruction(Instruction(
                    kind=InstructionKind.DECLARATION,
                    text=text,
                    ast_node=decl,
                    range=decl.range,
                    defined_vars=defined,
                    used_vars=used
                ))
            return current_block

        if isinstance(stmt, ExpressionStatement):
            if stmt.expression is not None:
                expr = stmt.expression
                defined = set()
                used = extract_used_vars(expr)
                kind = InstructionKind.EXPRESSION

                if isinstance(expr, AssignmentExpression):
                    kind = InstructionKind.ASSIGNMENT
                    defined.add(expr.target.name)
                elif isinstance(expr, UnaryExpression) and expr.operator in ("++", "--"):
                    kind = InstructionKind.ASSIGNMENT
                    if isinstance(expr.operand, IdentifierExpression):
                        defined.add(expr.operand.name)
                        used.add(expr.operand.name)

                current_block.add_instruction(Instruction(
                    kind=kind,
                    text=stringify_expr(expr),
                    ast_node=expr,
                    range=expr.range,
                    defined_vars=defined,
                    used_vars=used
                ))
            return current_block

        if isinstance(stmt, IfStatement):
            cond_text = stringify_expr(stmt.condition)
            current_block.add_instruction(Instruction(
                kind=InstructionKind.BRANCH,
                text=f"if ({cond_text})",
                ast_node=stmt.condition,
                range=stmt.condition.range,
                defined_vars=set(),
                used_vars=extract_used_vars(stmt.condition)
            ))

            then_block = self._new_block("if_then_")
            else_block = self._new_block("if_else_") if stmt.else_branch else None
            merge_block = self._new_block("if_merge_")

            self.cfg.add_edge(current_block, then_block, EdgeKind.TRUE_BRANCH, "true")

            if else_block:
                self.cfg.add_edge(current_block, else_block, EdgeKind.FALSE_BRANCH, "false")
            else:
                self.cfg.add_edge(current_block, merge_block, EdgeKind.FALSE_BRANCH, "false")

            then_end = self._build_statement(stmt.then_branch, then_block)
            if then_end is not None:
                self.cfg.add_edge(then_end, merge_block, EdgeKind.FALLTHROUGH)

            if else_block and stmt.else_branch:
                else_end = self._build_statement(stmt.else_branch, else_block)
                if else_end is not None:
                    self.cfg.add_edge(else_end, merge_block, EdgeKind.FALLTHROUGH)

            return merge_block

        if isinstance(stmt, WhileStatement):
            header_block = self._new_block("while_header_")
            body_block = self._new_block("while_body_")
            exit_block = self._new_block("while_exit_")

            self.cfg.add_edge(current_block, header_block, EdgeKind.FALLTHROUGH)

            cond_text = stringify_expr(stmt.condition)
            header_block.add_instruction(Instruction(
                kind=InstructionKind.BRANCH,
                text=f"while ({cond_text})",
                ast_node=stmt.condition,
                range=stmt.condition.range,
                defined_vars=set(),
                used_vars=extract_used_vars(stmt.condition)
            ))

            self.cfg.add_edge(header_block, body_block, EdgeKind.TRUE_BRANCH, "true")
            self.cfg.add_edge(header_block, exit_block, EdgeKind.FALSE_BRANCH, "false")

            self.loop_stack.append((header_block, exit_block))
            body_end = self._build_statement(stmt.body, body_block)
            self.loop_stack.pop()

            if body_end is not None:
                self.cfg.add_edge(body_end, header_block, EdgeKind.JUMP, "loop")

            return exit_block

        if isinstance(stmt, ForStatement):
            # Init clause
            if stmt.init is not None:
                current_block = self._build_statement(stmt.init, current_block)
                if current_block is None:
                    current_block = self._new_block("for_init_")

            header_block = self._new_block("for_header_")
            body_block = self._new_block("for_body_")
            step_block = self._new_block("for_step_")
            exit_block = self._new_block("for_exit_")

            self.cfg.add_edge(current_block, header_block, EdgeKind.FALLTHROUGH)

            if stmt.condition is not None:
                cond_text = stringify_expr(stmt.condition)
                header_block.add_instruction(Instruction(
                    kind=InstructionKind.BRANCH,
                    text=f"for_cond ({cond_text})",
                    ast_node=stmt.condition,
                    range=stmt.condition.range,
                    defined_vars=set(),
                    used_vars=extract_used_vars(stmt.condition)
                ))
            else:
                header_block.add_instruction(Instruction(
                    kind=InstructionKind.BRANCH,
                    text="for_cond (true)",
                    ast_node=None,
                    range=stmt.range,
                    defined_vars=set(),
                    used_vars=set()
                ))

            self.cfg.add_edge(header_block, body_block, EdgeKind.TRUE_BRANCH, "true")
            self.cfg.add_edge(header_block, exit_block, EdgeKind.FALSE_BRANCH, "false")

            # Step instruction in step_block
            if stmt.step is not None:
                step_def = set()
                step_use = extract_used_vars(stmt.step)
                if isinstance(stmt.step, AssignmentExpression):
                    step_def.add(stmt.step.target.name)
                elif isinstance(stmt.step, UnaryExpression) and stmt.step.operator in ("++", "--"):
                    if isinstance(stmt.step.operand, IdentifierExpression):
                        step_def.add(stmt.step.operand.name)
                        step_use.add(stmt.step.operand.name)

                step_block.add_instruction(Instruction(
                    kind=InstructionKind.EXPRESSION,
                    text=stringify_expr(stmt.step),
                    ast_node=stmt.step,
                    range=stmt.step.range,
                    defined_vars=step_def,
                    used_vars=step_use
                ))
            self.cfg.add_edge(step_block, header_block, EdgeKind.JUMP, "loop")

            # Loop body
            self.loop_stack.append((step_block, exit_block))
            body_end = self._build_statement(stmt.body, body_block)
            self.loop_stack.pop()

            if body_end is not None:
                self.cfg.add_edge(body_end, step_block, EdgeKind.FALLTHROUGH)

            return exit_block

        if isinstance(stmt, ReturnStatement):
            used = set()
            text = "return"
            if stmt.expression is not None:
                text += f" {stringify_expr(stmt.expression)}"
                used = extract_used_vars(stmt.expression)

            current_block.add_instruction(Instruction(
                kind=InstructionKind.RETURN,
                text=text,
                ast_node=stmt,
                range=stmt.range,
                defined_vars=set(),
                used_vars=used
            ))

            if self.cfg.exit_block is not None:
                self.cfg.add_edge(current_block, self.cfg.exit_block, EdgeKind.RETURN, "return")
            # Following statements in current block are unreachable
            return None

        if isinstance(stmt, BreakStatement):
            current_block.add_instruction(Instruction(
                kind=InstructionKind.BRANCH,
                text="break",
                ast_node=stmt,
                range=stmt.range
            ))
            if self.loop_stack:
                _, break_target = self.loop_stack[-1]
                self.cfg.add_edge(current_block, break_target, EdgeKind.JUMP, "break")
            return None

        if isinstance(stmt, ContinueStatement):
            current_block.add_instruction(Instruction(
                kind=InstructionKind.BRANCH,
                text="continue",
                ast_node=stmt,
                range=stmt.range
            ))
            if self.loop_stack:
                continue_target, _ = self.loop_stack[-1]
                self.cfg.add_edge(current_block, continue_target, EdgeKind.JUMP, "continue")
            return None

        return current_block
