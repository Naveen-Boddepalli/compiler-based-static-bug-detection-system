"""Abstract Syntax Tree (AST) node definitions for C-like language subset."""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from ..common.source_location import SourceRange, SourceLocation


class ASTNode:
    """Base class for all AST nodes."""
    range: SourceRange

    def accept(self, visitor: "ASTVisitor") -> Any:
        method_name = f"visit_{self.__class__.__name__}"
        visitor_fn = getattr(visitor, method_name, visitor.generic_visit)
        return visitor_fn(self)

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable representation for UI tree views."""
        return {
            "node_type": self.__class__.__name__,
            "range": self.range.to_dict() if hasattr(self, "range") and self.range else None
        }


# Types
@dataclass
class TypeNode(ASTNode):
    name: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["name"] = self.name
        return d


# Expressions
class Expression(ASTNode):
    """Base class for expression nodes."""
    pass


@dataclass
class IdentifierExpression(Expression):
    name: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["name"] = self.name
        return d


@dataclass
class IntegerLiteralExpression(Expression):
    value: int
    raw: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["value"] = self.value
        d["raw"] = self.raw
        return d


@dataclass
class FloatLiteralExpression(Expression):
    value: float
    raw: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["value"] = self.value
        d["raw"] = self.raw
        return d


@dataclass
class CharLiteralExpression(Expression):
    value: str
    raw: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["value"] = self.value
        d["raw"] = self.raw
        return d


@dataclass
class StringLiteralExpression(Expression):
    value: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["value"] = self.value
        return d


@dataclass
class BoolLiteralExpression(Expression):
    value: bool
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["value"] = self.value
        return d


@dataclass
class BinaryExpression(Expression):
    left: Expression
    operator: str
    right: Expression
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["operator"] = self.operator
        d["left"] = self.left.to_dict()
        d["right"] = self.right.to_dict()
        return d


@dataclass
class UnaryExpression(Expression):
    operator: str
    operand: Expression
    is_prefix: bool
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["operator"] = self.operator
        d["is_prefix"] = self.is_prefix
        d["operand"] = self.operand.to_dict()
        return d


@dataclass
class AssignmentExpression(Expression):
    target: IdentifierExpression
    operator: str
    value: Expression
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["target"] = self.target.to_dict()
        d["operator"] = self.operator
        d["value"] = self.value.to_dict()
        return d


@dataclass
class FunctionCallExpression(Expression):
    callee: str
    arguments: List[Expression]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["callee"] = self.callee
        d["arguments"] = [arg.to_dict() for arg in self.arguments]
        return d


@dataclass
class GroupedExpression(Expression):
    expression: Expression
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["expression"] = self.expression.to_dict()
        return d


# Statements and Declarations
class Statement(ASTNode):
    """Base class for statement nodes."""
    pass


@dataclass
class VarDeclarator(ASTNode):
    name: str
    initializer: Optional[Expression]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["name"] = self.name
        d["initializer"] = self.initializer.to_dict() if self.initializer else None
        return d


@dataclass
class VariableDeclaration(Statement):
    type_node: TypeNode
    declarators: List[VarDeclarator]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["type"] = self.type_node.to_dict()
        d["declarators"] = [dec.to_dict() for dec in self.declarators]
        return d


@dataclass
class CompoundStatement(Statement):
    statements: List[ASTNode]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["statements"] = [stmt.to_dict() for stmt in self.statements]
        return d


@dataclass
class ExpressionStatement(Statement):
    expression: Optional[Expression]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["expression"] = self.expression.to_dict() if self.expression else None
        return d


@dataclass
class IfStatement(Statement):
    condition: Expression
    then_branch: Statement
    else_branch: Optional[Statement]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["condition"] = self.condition.to_dict()
        d["then_branch"] = self.then_branch.to_dict()
        d["else_branch"] = self.else_branch.to_dict() if self.else_branch else None
        return d


@dataclass
class WhileStatement(Statement):
    condition: Expression
    body: Statement
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["condition"] = self.condition.to_dict()
        d["body"] = self.body.to_dict()
        return d


@dataclass
class ForStatement(Statement):
    init: Optional[ASTNode]  # VariableDeclaration or ExpressionStatement or None
    condition: Optional[Expression]
    step: Optional[Expression]
    body: Statement
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["init"] = self.init.to_dict() if self.init else None
        d["condition"] = self.condition.to_dict() if self.condition else None
        d["step"] = self.step.to_dict() if self.step else None
        d["body"] = self.body.to_dict()
        return d


@dataclass
class ReturnStatement(Statement):
    expression: Optional[Expression]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["expression"] = self.expression.to_dict() if self.expression else None
        return d


@dataclass
class BreakStatement(Statement):
    range: SourceRange


@dataclass
class ContinueStatement(Statement):
    range: SourceRange


@dataclass
class FunctionParameter(ASTNode):
    type_node: TypeNode
    name: str
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["type"] = self.type_node.to_dict()
        d["name"] = self.name
        return d


@dataclass
class FunctionDeclaration(ASTNode):
    return_type: TypeNode
    name: str
    parameters: List[FunctionParameter]
    body: Optional[CompoundStatement]
    is_prototype: bool
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["return_type"] = self.return_type.to_dict()
        d["name"] = self.name
        d["parameters"] = [p.to_dict() for p in self.parameters]
        d["body"] = self.body.to_dict() if self.body else None
        d["is_prototype"] = self.is_prototype
        return d


@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]
    range: SourceRange

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["declarations"] = [decl.to_dict() for decl in self.declarations]
        return d


class ASTVisitor:
    """Base visitor class with default traversal behavior."""

    def generic_visit(self, node: ASTNode) -> Any:
        return None
