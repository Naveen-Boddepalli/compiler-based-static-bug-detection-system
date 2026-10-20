"""Base detector class for static analysis inspection passes."""

from abc import ABC, abstractmethod
from typing import List
from ..common.diagnostic import Diagnostic
from ..parser.ast_nodes import Program
from ..semantics.symbol_table import SymbolTable
from ..cfg.basic_block import ControlFlowGraph


class BaseDetector(ABC):
    """Abstract base class for static analysis bug detectors."""

    @abstractmethod
    def run(self, program: Program, symbol_table: SymbolTable, cfgs: List[ControlFlowGraph]) -> List[Diagnostic]:
        """Executes the detector pass and returns identified diagnostics."""
        pass
