"""Recursive descent parser with operator precedence and error recovery."""

from typing import List, Tuple, Optional
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..lexer.tokens import Token, TokenType
from .ast_nodes import (
    ASTNode, Program, TypeNode, VariableDeclaration, VarDeclarator,
    FunctionDeclaration, FunctionParameter, CompoundStatement,
    ExpressionStatement, IfStatement, WhileStatement, ForStatement,
    ReturnStatement, BreakStatement, ContinueStatement,
    Expression, IdentifierExpression, IntegerLiteralExpression,
    FloatLiteralExpression, CharLiteralExpression, StringLiteralExpression,
    BoolLiteralExpression, BinaryExpression, UnaryExpression,
    AssignmentExpression, FunctionCallExpression, GroupedExpression
)


TYPE_TOKENS = {
    TokenType.KW_INT: "int",
    TokenType.KW_FLOAT: "float",
    TokenType.KW_CHAR: "char",
    TokenType.KW_VOID: "void",
    TokenType.KW_BOOL: "bool",
}

ASSIGN_OPERATORS = {
    TokenType.ASSIGN: "=",
    TokenType.PLUS_ASSIGN: "+=",
    TokenType.MINUS_ASSIGN: "-=",
    TokenType.STAR_ASSIGN: "*=",
    TokenType.SLASH_ASSIGN: "/=",
    TokenType.PERCENT_ASSIGN: "%=",
}


class Parser:
    """Parses a sequence of tokens into an AST representation."""

    def __init__(self, tokens: List[Token], filename: str = "<input>"):
        self.tokens = tokens
        self.filename = filename
        self.cursor = 0
        self.diagnostics: List[Diagnostic] = []

    def _current(self) -> Token:
        if self.cursor < len(self.tokens):
            return self.tokens[self.cursor]
        return self.tokens[-1]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.cursor + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _is_at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _advance(self) -> Token:
        tok = self._current()
        if not self._is_at_end():
            self.cursor += 1
        return tok

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._current().type == token_type

    def _match(self, *token_types: TokenType) -> bool:
        for tt in token_types:
            if self._check(tt):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, error_code: str, message: str, suggestion: Optional[str] = None) -> Token:
        if self._check(token_type):
            return self._advance()

        cur = self._current()
        self.diagnostics.append(Diagnostic(
            severity=Severity.ERROR,
            category=DiagnosticCategory.SYNTAX,
            code=error_code,
            message=message,
            location=cur.start_location,
            range=cur.range,
            suggestion=suggestion
        ))
        # Return a synthetic token of expected type so downstream AST nodes avoid type confusion
        return Token(token_type, f"<missing_{token_type.name}>", None, cur.range)

    def _synchronize(self):
        """Advances until finding a statement boundary to resume parsing."""
        self._advance()
        while not self._is_at_end():
            if self.tokens[self.cursor - 1].type == TokenType.SEMICOLON:
                return
            if self._current().type in (
                TokenType.KW_IF, TokenType.KW_WHILE, TokenType.KW_FOR,
                TokenType.KW_RETURN, TokenType.KW_INT, TokenType.KW_FLOAT,
                TokenType.KW_CHAR, TokenType.KW_VOID, TokenType.KW_BOOL,
                TokenType.LBRACE, TokenType.RBRACE
            ):
                return
            self._advance()

    def parse(self) -> Tuple[Program, List[Diagnostic]]:
        """Parses the full token stream into a Program AST."""
        start_loc = self._current().start_location
        declarations: List[ASTNode] = []

        while not self._is_at_end():
            try:
                decl = self._parse_external_declaration()
                if decl is not None:
                    declarations.append(decl)
            except Exception:
                self._synchronize()

        end_loc = self._current().range.end
        prog = Program(declarations=declarations, range=SourceRange(start_loc, end_loc))
        return prog, self.diagnostics

    # -------------------------------------------------------------
    # Declarations
    # -------------------------------------------------------------

    def _is_type_specifier(self) -> bool:
        return self._current().type in TYPE_TOKENS

    def _parse_type_specifier(self) -> TypeNode:
        cur = self._current()
        if self._is_type_specifier():
            self._advance()
            return TypeNode(name=TYPE_TOKENS[cur.type], range=cur.range)

        self.diagnostics.append(Diagnostic(
            severity=Severity.ERROR,
            category=DiagnosticCategory.SYNTAX,
            code="SYN-010",
            message=f"Expected type specifier (int, float, char, void, bool), got '{cur.lexeme}'",
            location=cur.start_location,
            range=cur.range,
            suggestion="Specify a valid type name"
        ))
        return TypeNode(name="int", range=cur.range)

    def _parse_external_declaration(self) -> Optional[ASTNode]:
        """Parses a top-level function definition/declaration, global variable declaration, or statement."""
        if self._is_type_specifier():
            type_node = self._parse_type_specifier()

            # Check if function or variable
            # Look ahead for: type identifier ( ...
            if self._check(TokenType.IDENTIFIER) and self._peek().type == TokenType.LPAREN:
                return self._parse_function_declaration(type_node)
            else:
                return self._parse_variable_declaration(type_node)

        # Allow top-level statements for script/snippet inputs without main()
        cur_type = self._current().type
        if cur_type in (
            TokenType.KW_IF, TokenType.KW_WHILE, TokenType.KW_FOR,
            TokenType.KW_RETURN, TokenType.KW_BREAK, TokenType.KW_CONTINUE,
            TokenType.LBRACE, TokenType.SEMICOLON, TokenType.IDENTIFIER,
            TokenType.LPAREN, TokenType.INCREMENT, TokenType.DECREMENT,
            TokenType.PLUS, TokenType.MINUS, TokenType.LOGICAL_NOT
        ):
            return self._parse_statement()

        cur = self._current()
        self.diagnostics.append(Diagnostic(
            severity=Severity.ERROR,
            category=DiagnosticCategory.SYNTAX,
            code="SYN-011",
            message=f"Expected declaration specifier or statement, got '{cur.lexeme}'",
            location=cur.start_location,
            range=cur.range,
            suggestion="Declare a function, variable, or statement"
        ))
        self._synchronize()
        return None

    def _parse_function_declaration(self, return_type: TypeNode) -> Optional[FunctionDeclaration]:
        name_tok = self._consume(TokenType.IDENTIFIER, "SYN-012", "Expected function name")
        self._consume(TokenType.LPAREN, "SYN-013", "Expected '(' after function name")

        params: List[FunctionParameter] = []
        if not self._check(TokenType.RPAREN):
            # Check for void parameter: foo(void)
            if self._check(TokenType.KW_VOID) and self._peek().type == TokenType.RPAREN:
                self._advance() # void
            else:
                while True:
                    p_type = self._parse_type_specifier()
                    p_name_tok = self._consume(TokenType.IDENTIFIER, "SYN-014", "Expected parameter name")
                    p_range = SourceRange(p_type.range.start, p_name_tok.range.end)
                    params.append(FunctionParameter(type_node=p_type, name=p_name_tok.lexeme, range=p_range))
                    if not self._match(TokenType.COMMA):
                        break

        rparen_tok = self._consume(TokenType.RPAREN, "SYN-015", "Expected ')' after parameter list")

        # Function definition with body or prototype with semicolon
        if self._match(TokenType.SEMICOLON):
            fn_range = SourceRange(return_type.range.start, rparen_tok.range.end)
            return FunctionDeclaration(
                return_type=return_type,
                name=name_tok.lexeme,
                parameters=params,
                body=None,
                is_prototype=True,
                range=fn_range
            )
        elif self._check(TokenType.LBRACE):
            body = self._parse_compound_statement()
            fn_range = SourceRange(return_type.range.start, body.range.end)
            return FunctionDeclaration(
                return_type=return_type,
                name=name_tok.lexeme,
                parameters=params,
                body=body,
                is_prototype=False,
                range=fn_range
            )
        else:
            cur = self._current()
            self.diagnostics.append(Diagnostic(
                severity=Severity.ERROR,
                category=DiagnosticCategory.SYNTAX,
                code="SYN-016",
                message=f"Expected '{{' or ';' after function declarator, got '{cur.lexeme}'",
                location=cur.start_location,
                range=cur.range,
                suggestion="Add function body or terminate prototype with ';'"
            ))
            self._synchronize()
            return None

    def _parse_variable_declaration(self, type_node: TypeNode) -> VariableDeclaration:
        declarators: List[VarDeclarator] = []
        start_loc = type_node.range.start

        while True:
            if not self._check(TokenType.IDENTIFIER):
                cur = self._current()
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SYNTAX,
                    code="SYN-017",
                    message=f"Expected variable identifier, got '{cur.lexeme}'",
                    location=cur.start_location,
                    range=cur.range,
                    suggestion="Specify a valid variable identifier"
                ))
                if not self._check(TokenType.SEMICOLON) and not self._is_at_end():
                    self._advance()
                break

            id_tok = self._advance()
            init_expr: Optional[Expression] = None
            end_loc = id_tok.range.end

            if self._match(TokenType.ASSIGN):
                init_expr = self._parse_expression()
                end_loc = init_expr.range.end

            declarators.append(VarDeclarator(
                name=id_tok.lexeme,
                initializer=init_expr,
                range=SourceRange(id_tok.range.start, end_loc)
            ))

            if not self._match(TokenType.COMMA):
                break

        semi_tok = self._consume(TokenType.SEMICOLON, "SYN-018", "Expected ';' at end of variable declaration", "Add ';'")
        decl_range = SourceRange(start_loc, semi_tok.range.end)
        return VariableDeclaration(type_node=type_node, declarators=declarators, range=decl_range)

    # -------------------------------------------------------------
    # Statements
    # -------------------------------------------------------------

    def _parse_statement(self) -> ASTNode:
        if self._check(TokenType.LBRACE):
            return self._parse_compound_statement()
        if self._check(TokenType.KW_IF):
            return self._parse_if_statement()
        if self._check(TokenType.KW_WHILE):
            return self._parse_while_statement()
        if self._check(TokenType.KW_FOR):
            return self._parse_for_statement()
        if self._check(TokenType.KW_RETURN):
            return self._parse_return_statement()
        if self._check(TokenType.KW_BREAK):
            return self._parse_break_statement()
        if self._check(TokenType.KW_CONTINUE):
            return self._parse_continue_statement()
        if self._is_type_specifier():
            type_node = self._parse_type_specifier()
            return self._parse_variable_declaration(type_node)
        if self._match(TokenType.SEMICOLON):
            loc = self.tokens[self.cursor - 1].range
            return ExpressionStatement(expression=None, range=loc)

        return self._parse_expression_statement()

    def _parse_compound_statement(self) -> CompoundStatement:
        lbrace = self._consume(TokenType.LBRACE, "SYN-020", "Expected '{'")
        stmts: List[ASTNode] = []

        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    stmts.append(stmt)
            except Exception:
                self._synchronize()

        rbrace = self._consume(TokenType.RBRACE, "SYN-021", "Expected '}' to close block")
        return CompoundStatement(statements=stmts, range=SourceRange(lbrace.range.start, rbrace.range.end))

    def _parse_if_statement(self) -> IfStatement:
        if_tok = self._consume(TokenType.KW_IF, "SYN-022", "Expected 'if'")
        self._consume(TokenType.LPAREN, "SYN-023", "Expected '(' after 'if'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "SYN-024", "Expected ')' after if condition")

        then_branch = self._parse_statement()
        else_branch: Optional[ASTNode] = None
        end_loc = then_branch.range.end

        if self._match(TokenType.KW_ELSE):
            else_branch = self._parse_statement()
            end_loc = else_branch.range.end

        return IfStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            range=SourceRange(if_tok.range.start, end_loc)
        )

    def _parse_while_statement(self) -> WhileStatement:
        while_tok = self._consume(TokenType.KW_WHILE, "SYN-025", "Expected 'while'")
        self._consume(TokenType.LPAREN, "SYN-026", "Expected '(' after 'while'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "SYN-027", "Expected ')' after while condition")
        body = self._parse_statement()
        return WhileStatement(
            condition=condition,
            body=body,
            range=SourceRange(while_tok.range.start, body.range.end)
        )

    def _parse_for_statement(self) -> ForStatement:
        for_tok = self._consume(TokenType.KW_FOR, "SYN-028", "Expected 'for'")
        self._consume(TokenType.LPAREN, "SYN-029", "Expected '(' after 'for'")

        init_node: Optional[ASTNode] = None
        if self._is_type_specifier():
            t_node = self._parse_type_specifier()
            init_node = self._parse_variable_declaration(t_node)
        elif not self._match(TokenType.SEMICOLON):
            init_expr = self._parse_expression()
            semi = self._consume(TokenType.SEMICOLON, "SYN-030", "Expected ';' after for init expression")
            init_node = ExpressionStatement(expression=init_expr, range=SourceRange(init_expr.range.start, semi.range.end))

        condition: Optional[Expression] = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "SYN-031", "Expected ';' after for condition")

        step: Optional[Expression] = None
        if not self._check(TokenType.RPAREN):
            step = self._parse_expression()
        self._consume(TokenType.RPAREN, "SYN-032", "Expected ')' after for clauses")

        body = self._parse_statement()
        return ForStatement(
            init=init_node,
            condition=condition,
            step=step,
            body=body,
            range=SourceRange(for_tok.range.start, body.range.end)
        )

    def _parse_return_statement(self) -> ReturnStatement:
        ret_tok = self._consume(TokenType.KW_RETURN, "SYN-033", "Expected 'return'")
        expr: Optional[Expression] = None
        if not self._check(TokenType.SEMICOLON):
            expr = self._parse_expression()
        semi_tok = self._consume(TokenType.SEMICOLON, "SYN-034", "Expected ';' after return")
        return ReturnStatement(
            expression=expr,
            range=SourceRange(ret_tok.range.start, semi_tok.range.end)
        )

    def _parse_break_statement(self) -> BreakStatement:
        tok = self._consume(TokenType.KW_BREAK, "SYN-035", "Expected 'break'")
        semi = self._consume(TokenType.SEMICOLON, "SYN-036", "Expected ';' after break")
        return BreakStatement(range=SourceRange(tok.range.start, semi.range.end))

    def _parse_continue_statement(self) -> ContinueStatement:
        tok = self._consume(TokenType.KW_CONTINUE, "SYN-037", "Expected 'continue'")
        semi = self._consume(TokenType.SEMICOLON, "SYN-038", "Expected ';' after continue")
        return ContinueStatement(range=SourceRange(tok.range.start, semi.range.end))

    def _parse_expression_statement(self) -> ExpressionStatement:
        expr = self._parse_expression()
        semi = self._consume(TokenType.SEMICOLON, "SYN-039", "Expected ';' after expression", "Add ';'")
        return ExpressionStatement(expression=expr, range=SourceRange(expr.range.start, semi.range.end))

    # -------------------------------------------------------------
    # Expressions (Operator Precedence)
    # -------------------------------------------------------------

    def _parse_expression(self) -> Expression:
        return self._parse_assignment()

    def _parse_assignment(self) -> Expression:
        expr = self._parse_logical_or()

        if self._current().type in ASSIGN_OPERATORS:
            op_tok = self._advance()
            op_str = ASSIGN_OPERATORS[op_tok.type]
            value = self._parse_assignment()

            if isinstance(expr, IdentifierExpression):
                return AssignmentExpression(
                    target=expr,
                    operator=op_str,
                    value=value,
                    range=SourceRange(expr.range.start, value.range.end)
                )
            else:
                self.diagnostics.append(Diagnostic(
                    severity=Severity.ERROR,
                    category=DiagnosticCategory.SYNTAX,
                    code="SYN-040",
                    message="Invalid assignment target; left-hand side must be a variable",
                    location=expr.range.start,
                    range=expr.range,
                    suggestion="Assign to a valid variable identifier"
                ))
        return expr

    def _parse_logical_or(self) -> Expression:
        expr = self._parse_logical_and()
        while self._match(TokenType.LOGICAL_OR):
            op_str = "||"
            right = self._parse_logical_and()
            expr = BinaryExpression(
                left=expr,
                operator=op_str,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_logical_and(self) -> Expression:
        expr = self._parse_equality()
        while self._match(TokenType.LOGICAL_AND):
            op_str = "&&"
            right = self._parse_equality()
            expr = BinaryExpression(
                left=expr,
                operator=op_str,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_equality(self) -> Expression:
        expr = self._parse_relational()
        while self._current().type in (TokenType.EQ, TokenType.NEQ):
            op_tok = self._advance()
            right = self._parse_relational()
            expr = BinaryExpression(
                left=expr,
                operator=op_tok.lexeme,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_relational(self) -> Expression:
        expr = self._parse_additive()
        while self._current().type in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op_tok = self._advance()
            right = self._parse_additive()
            expr = BinaryExpression(
                left=expr,
                operator=op_tok.lexeme,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_additive(self) -> Expression:
        expr = self._parse_multiplicative()
        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            expr = BinaryExpression(
                left=expr,
                operator=op_tok.lexeme,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_multiplicative(self) -> Expression:
        expr = self._parse_unary()
        while self._current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._advance()
            right = self._parse_unary()
            expr = BinaryExpression(
                left=expr,
                operator=op_tok.lexeme,
                right=right,
                range=SourceRange(expr.range.start, right.range.end)
            )
        return expr

    def _parse_unary(self) -> Expression:
        if self._current().type in (TokenType.MINUS, TokenType.PLUS, TokenType.LOGICAL_NOT, TokenType.INCREMENT, TokenType.DECREMENT):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryExpression(
                operator=op_tok.lexeme,
                operand=operand,
                is_prefix=True,
                range=SourceRange(op_tok.range.start, operand.range.end)
            )
        return self._parse_postfix()

    def _parse_postfix(self) -> Expression:
        expr = self._parse_primary()

        while True:
            # Postfix ++ or --
            if self._current().type in (TokenType.INCREMENT, TokenType.DECREMENT):
                op_tok = self._advance()
                expr = UnaryExpression(
                    operator=op_tok.lexeme,
                    operand=expr,
                    is_prefix=False,
                    range=SourceRange(expr.range.start, op_tok.range.end)
                )
            # Function call
            elif self._match(TokenType.LPAREN):
                args: List[Expression] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                rparen_tok = self._consume(TokenType.RPAREN, "SYN-041", "Expected ')' after call arguments")
                callee_name = expr.name if isinstance(expr, IdentifierExpression) else "<expr>"
                expr = FunctionCallExpression(
                    callee=callee_name,
                    arguments=args,
                    range=SourceRange(expr.range.start, rparen_tok.range.end)
                )
            else:
                break

        return expr

    def _parse_primary(self) -> Expression:
        cur = self._current()

        if self._match(TokenType.INT_LITERAL):
            return IntegerLiteralExpression(value=cur.value, raw=cur.lexeme, range=cur.range)

        if self._match(TokenType.FLOAT_LITERAL):
            return FloatLiteralExpression(value=cur.value, raw=cur.lexeme, range=cur.range)

        if self._match(TokenType.CHAR_LITERAL):
            return CharLiteralExpression(value=cur.value, raw=cur.lexeme, range=cur.range)

        if self._match(TokenType.STRING_LITERAL):
            return StringLiteralExpression(value=cur.value, range=cur.range)

        if self._match(TokenType.BOOL_LITERAL):
            return BoolLiteralExpression(value=cur.value, range=cur.range)

        if self._match(TokenType.IDENTIFIER):
            return IdentifierExpression(name=cur.lexeme, range=cur.range)

        if self._match(TokenType.LPAREN):
            inner = self._parse_expression()
            rparen = self._consume(TokenType.RPAREN, "SYN-042", "Expected ')' to close grouped expression")
            return GroupedExpression(expression=inner, range=SourceRange(cur.range.start, rparen.range.end))

        # Recovery placeholder
        self.diagnostics.append(Diagnostic(
            severity=Severity.ERROR,
            category=DiagnosticCategory.SYNTAX,
            code="SYN-043",
            message=f"Expected expression, got '{cur.lexeme}'",
            location=cur.start_location,
            range=cur.range,
            suggestion="Provide a valid expression or literal"
        ))
        self._advance()
        return IntegerLiteralExpression(value=0, raw="0", range=cur.range)
