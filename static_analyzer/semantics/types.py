"""Type representation and type checking rules for C-like language subset."""

from dataclasses import dataclass
from typing import List, Optional


class CType:
    """Base class for C subset types."""
    name: str

    def is_numeric(self) -> bool:
        return False

    def is_integral(self) -> bool:
        return False

    def is_boolean(self) -> bool:
        return False

    def is_void(self) -> bool:
        return False

    def is_compatible_with(self, other: "CType") -> bool:
        if isinstance(self, ErrorType) or isinstance(other, ErrorType):
            return True
        return self == other

    def __str__(self) -> str:
        return self.name


class IntType(CType):
    name = "int"

    def is_numeric(self) -> bool:
        return True

    def is_integral(self) -> bool:
        return True

    def is_compatible_with(self, other: "CType") -> bool:
        if isinstance(other, (IntType, BoolType, CharType)):
            return True
        return super().is_compatible_with(other)

    def __eq__(self, other):
        return isinstance(other, IntType)

    def __hash__(self):
        return hash(self.name)


class FloatType(CType):
    name = "float"

    def is_numeric(self) -> bool:
        return True

    def is_compatible_with(self, other: "CType") -> bool:
        if isinstance(other, (FloatType, IntType)):
            return True
        return super().is_compatible_with(other)

    def __eq__(self, other):
        return isinstance(other, FloatType)

    def __hash__(self):
        return hash(self.name)


class CharType(CType):
    name = "char"

    def is_integral(self) -> bool:
        return True

    def is_compatible_with(self, other: "CType") -> bool:
        if isinstance(other, (CharType, IntType)):
            return True
        return super().is_compatible_with(other)

    def __eq__(self, other):
        return isinstance(other, CharType)

    def __hash__(self):
        return hash(self.name)


class BoolType(CType):
    name = "bool"

    def is_boolean(self) -> bool:
        return True

    def is_compatible_with(self, other: "CType") -> bool:
        if isinstance(other, (BoolType, IntType)):
            return True
        return super().is_compatible_with(other)

    def __eq__(self, other):
        return isinstance(other, BoolType)

    def __hash__(self):
        return hash(self.name)


class VoidType(CType):
    name = "void"

    def is_void(self) -> bool:
        return True

    def __eq__(self, other):
        return isinstance(other, VoidType)

    def __hash__(self):
        return hash(self.name)


class ErrorType(CType):
    name = "<error>"

    def is_compatible_with(self, other: "CType") -> bool:
        return True

    def __eq__(self, other):
        return isinstance(other, ErrorType)

    def __hash__(self):
        return hash(self.name)


@dataclass
class FunctionType(CType):
    return_type: CType
    param_types: List[CType]

    @property
    def name(self) -> str:
        params_str = ", ".join(p.name for p in self.param_types)
        return f"{self.return_type.name} ({params_str})"

    def __eq__(self, other):
        if not isinstance(other, FunctionType):
            return False
        return self.return_type == other.return_type and self.param_types == other.param_types

    def __hash__(self):
        return hash((self.return_type, tuple(self.param_types)))


TYPE_REGISTRY = {
    "int": IntType(),
    "float": FloatType(),
    "char": CharType(),
    "bool": BoolType(),
    "void": VoidType(),
}


def resolve_type_by_name(name: str) -> CType:
    return TYPE_REGISTRY.get(name, ErrorType())


def compute_binary_type(left: CType, op: str, right: CType) -> CType:
    """Computes resultant type for a binary operation or returns ErrorType if invalid."""
    if isinstance(left, ErrorType) or isinstance(right, ErrorType):
        return ErrorType()

    if left.is_void() or right.is_void():
        return ErrorType()

    # Relational and equality operators return bool
    if op in ("==", "!=", "<", "<=", ">", ">="):
        if (left.is_numeric() and right.is_numeric()) or (left.name == right.name):
            return BoolType()
        return ErrorType()

    # Logical operators return bool
    if op in ("&&", "||"):
        return BoolType()

    # Arithmetic operators
    if op in ("+", "-", "*", "/"):
        if left.is_numeric() and right.is_numeric():
            if isinstance(left, FloatType) or isinstance(right, FloatType):
                return FloatType()
            return IntType()
        return ErrorType()

    if op == "%":
        if left.is_integral() and right.is_integral():
            return IntType()
        return ErrorType()

    return ErrorType()
