"""Scoped Symbol Table for lexical analysis and semantic binding."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from ..common.source_location import SourceLocation, SourceRange
from .types import CType


class SymbolKind(Enum):
    VARIABLE = "VARIABLE"
    PARAMETER = "PARAMETER"
    FUNCTION = "FUNCTION"


@dataclass
class Symbol:
    name: str
    type: CType
    kind: SymbolKind
    declared_location: SourceLocation
    declared_range: SourceRange
    scope_id: int
    is_initialized: bool = False
    is_used: bool = False
    use_locations: List[SourceLocation] = field(default_factory=list)
    assignment_locations: List[SourceLocation] = field(default_factory=list)

    def mark_used(self, location: SourceLocation):
        self.is_used = True
        self.use_locations.append(location)

    def mark_assigned(self, location: SourceLocation):
        self.is_initialized = True
        self.assignment_locations.append(location)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": str(self.type),
            "kind": self.kind.value,
            "declared_location": self.declared_location.to_dict(),
            "scope_id": self.scope_id,
            "is_initialized": self.is_initialized,
            "is_used": self.is_used,
            "use_count": len(self.use_locations),
            "assignment_count": len(self.assignment_locations),
        }


class Scope:
    """Represents a single lexical scope block."""

    def __init__(self, scope_id: int, name: str, parent: Optional["Scope"] = None):
        self.scope_id = scope_id
        self.name = name
        self.parent = parent
        self.children: List["Scope"] = []
        self.symbols: Dict[str, Symbol] = {}

    @property
    def depth(self) -> int:
        d = 0
        p = self.parent
        while p is not None:
            d += 1
            p = p.parent
        return d

    def define(self, symbol: Symbol) -> bool:
        """Defines a symbol in the current scope. Returns False if already declared in this exact scope."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "name": self.name,
            "depth": self.depth,
            "symbols": [s.to_dict() for s in self.symbols.values()],
            "children": [c.to_dict() for c in self.children]
        }


class SymbolTable:
    """Manages the full tree of lexical scopes and current scope navigation."""

    def __init__(self):
        self._next_id = 0
        self.root_scope = Scope(scope_id=self._generate_id(), name="global", parent=None)
        self.current_scope = self.root_scope
        self.all_scopes: List[Scope] = [self.root_scope]

    def _generate_id(self) -> int:
        sid = self._next_id
        self._next_id += 1
        return sid

    def enter_scope(self, name: str = "block") -> Scope:
        new_scope = Scope(scope_id=self._generate_id(), name=name, parent=self.current_scope)
        self.current_scope.children.append(new_scope)
        self.all_scopes.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self) -> Optional[Scope]:
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
        return self.current_scope

    def define(self, symbol: Symbol) -> bool:
        return self.current_scope.define(symbol)

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_local(name)

    def get_all_symbols(self) -> List[Symbol]:
        res = []
        for s in self.all_scopes:
            res.extend(s.symbols.values())
        return res

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_scope": self.root_scope.to_dict(),
            "total_scopes": len(self.all_scopes),
            "symbols_flat": [s.to_dict() for s in self.get_all_symbols()]
        }
