"""Basic Block, Control Flow Edge, and CFG Data Structures."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Any, Set
from ..common.source_location import SourceLocation, SourceRange
from ..parser.ast_nodes import ASTNode


class EdgeKind(Enum):
    FALLTHROUGH = "FALLTHROUGH"
    TRUE_BRANCH = "TRUE"
    FALSE_BRANCH = "FALSE"
    JUMP = "JUMP"
    RETURN = "RETURN"


class InstructionKind(Enum):
    DECLARATION = "DECL"
    ASSIGNMENT = "ASSIGN"
    EXPRESSION = "EXPR"
    BRANCH = "BRANCH"
    RETURN = "RET"
    NOP = "NOP"


@dataclass
class Instruction:
    """Represents a simplified linearized instruction inside a basic block."""
    kind: InstructionKind
    text: str
    ast_node: Optional[ASTNode] = None
    range: Optional[SourceRange] = None
    defined_vars: Set[str] = field(default_factory=set)
    used_vars: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "range": self.range.to_dict() if self.range else None,
            "defined_vars": list(self.defined_vars),
            "used_vars": list(self.used_vars),
        }


@dataclass
class CFGEdge:
    from_block_id: int
    to_block_id: int
    kind: EdgeKind
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_block_id,
            "to": self.to_block_id,
            "kind": self.kind.value,
            "label": self.label
        }


class BasicBlock:
    """A straight-line sequence of instructions with one entry and one exit."""

    def __init__(self, block_id: int, label: str):
        self.id = block_id
        self.label = label
        self.instructions: List[Instruction] = []
        self.predecessors: List["BasicBlock"] = []
        self.successors: List["BasicBlock"] = []
        self.outgoing_edges: List[CFGEdge] = []
        self.is_entry: bool = False
        self.is_exit: bool = False
        self.is_reachable: bool = True

        # Data-flow state annotations
        self.gen_set: Set[str] = set()
        self.kill_set: Set[str] = set()
        self.in_set: Set[str] = set()
        self.out_set: Set[str] = set()

    def add_instruction(self, inst: Instruction):
        self.instructions.append(inst)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "is_entry": self.is_entry,
            "is_exit": self.is_exit,
            "is_reachable": self.is_reachable,
            "instructions": [inst.to_dict() for inst in self.instructions],
            "predecessor_ids": [p.id for p in self.predecessors],
            "successor_ids": [s.id for s in self.successors],
            "in_vars": sorted(list(self.in_set)),
            "out_vars": sorted(list(self.out_set))
        }

    def __repr__(self) -> str:
        return f"Block(id={self.id}, label='{self.label}', insts={len(self.instructions)})"


class ControlFlowGraph:
    """Represents a Control Flow Graph for a single function."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        self.blocks: List[BasicBlock] = []
        self.edges: List[CFGEdge] = []
        self.entry_block: Optional[BasicBlock] = None
        self.exit_block: Optional[BasicBlock] = None
        self.scope: Any = None

    def add_block(self, block: BasicBlock):
        self.blocks.append(block)

    def add_edge(self, from_block: BasicBlock, to_block: BasicBlock, kind: EdgeKind, label: str = ""):
        from_block.successors.append(to_block)
        to_block.predecessors.append(from_block)
        edge = CFGEdge(
            from_block_id=from_block.id,
            to_block_id=to_block.id,
            kind=kind,
            label=label or (kind.value if kind != EdgeKind.FALLTHROUGH else "")
        )
        from_block.outgoing_edges.append(edge)
        self.edges.append(edge)

    def compute_reachability(self):
        """Performs BFS/DFS from entry_block to find all reachable blocks."""
        for b in self.blocks:
            b.is_reachable = False

        if not self.entry_block:
            return

        visited: Set[int] = set()
        queue = [self.entry_block]
        self.entry_block.is_reachable = True
        visited.add(self.entry_block.id)

        while queue:
            cur = queue.pop(0)
            for succ in cur.successors:
                if succ.id not in visited:
                    succ.is_reachable = True
                    visited.add(succ.id)
                    queue.append(succ)

    def get_unreachable_blocks(self) -> List[BasicBlock]:
        return [b for b in self.blocks if not b.is_reachable and not b.is_exit]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "entry_block_id": self.entry_block.id if self.entry_block else None,
            "exit_block_id": self.exit_block.id if self.exit_block else None,
            "blocks": [b.to_dict() for b in self.blocks],
            "edges": [e.to_dict() for e in self.edges],
            "total_blocks": len(self.blocks),
            "unreachable_count": len(self.get_unreachable_blocks())
        }
