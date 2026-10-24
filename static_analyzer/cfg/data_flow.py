"""Data-flow analysis engine computing definite assignment and variable states."""

from typing import Dict, Set, List, Tuple, Optional
from ..common.source_location import SourceLocation, SourceRange
from ..common.diagnostic import Diagnostic, Severity, DiagnosticCategory
from ..semantics.symbol_table import SymbolTable, Symbol, SymbolKind
from .basic_block import ControlFlowGraph, BasicBlock, Instruction, InstructionKind


class DataFlowAnalyzer:
    """Performs forward data-flow analysis to detect uninitialized and unused variables."""

    def __init__(self, cfg: ControlFlowGraph, symbol_table: SymbolTable):
        self.cfg = cfg
        self.symbol_table = symbol_table
        self.diagnostics: List[Diagnostic] = []

        # Maps block_id -> Set of variables guaranteed to be initialized at entry
        self.must_in: Dict[int, Set[str]] = {}
        # Maps block_id -> Set of variables guaranteed to be initialized at exit
        self.must_out: Dict[int, Set[str]] = {}

        # Maps block_id -> Set of variables that MAY be initialized at entry
        self.may_in: Dict[int, Set[str]] = {}
        # Maps block_id -> Set of variables that MAY be initialized at exit
        self.may_out: Dict[int, Set[str]] = {}

    def analyze(self) -> List[Diagnostic]:
        if not self.cfg.entry_block:
            return self.diagnostics

        self._compute_must_and_may_analysis()
        self._check_uninitialized_reads()
        return self.diagnostics

    def _compute_must_and_may_analysis(self):
        """Runs iterative forward data-flow analysis to find guaranteed and possible definitions."""
        all_blocks = self.cfg.blocks
        all_local_vars: Set[str] = set()

        for b in all_blocks:
            for inst in b.instructions:
                all_local_vars.update(inst.defined_vars)

        # Parameters of this function
        params = set()
        for inst in self.cfg.entry_block.instructions:
            if inst.kind == InstructionKind.DECLARATION and inst.text.startswith("param "):
                params.update(inst.defined_vars)

        # Initialized global variables
        globals_init = set()
        if self.symbol_table and self.symbol_table.root_scope:
            for s in self.symbol_table.root_scope.symbols.values():
                if s.kind == SymbolKind.VARIABLE and s.is_initialized:
                    globals_init.add(s.name)

        all_known_vars = all_local_vars | params | globals_init

        # Initialize sets
        # In intersection-meet data-flow analysis, non-entry blocks must start at TOP (all variables)
        for b in all_blocks:
            self.must_in[b.id] = set(all_known_vars)
            self.must_out[b.id] = set(all_known_vars)
            self.may_in[b.id] = set()
            self.may_out[b.id] = set()

        # Entry block starts with function parameters and initialized globals
        init_at_entry = params | globals_init
        self.must_in[self.cfg.entry_block.id] = set(init_at_entry)
        self.must_out[self.cfg.entry_block.id] = set(init_at_entry)
        self.may_in[self.cfg.entry_block.id] = set(init_at_entry)
        self.may_out[self.cfg.entry_block.id] = set(init_at_entry)

        # Iterate MUST-initialized (definite assignment - intersection meet)
        changed = True
        iterations = 0
        max_iters = len(all_blocks) * 4 + 10

        while changed and iterations < max_iters:
            changed = False
            iterations += 1

            for b in all_blocks:
                if not b.is_reachable and not b.is_entry:
                    continue

                if not b.is_entry:
                    # In = intersection of must_out across all REACHABLE predecessors
                    pred_outs = [self.must_out[p.id] for p in b.predecessors if p.is_reachable]
                    if pred_outs:
                        new_in = set(pred_outs[0])
                        for po in pred_outs[1:]:
                            new_in &= po
                    else:
                        new_in = set()

                    if new_in != self.must_in[b.id]:
                        self.must_in[b.id] = new_in
                        changed = True

                # Transfer function through block b
                current = set(self.must_in[b.id])
                for inst in b.instructions:
                    # Add newly defined variables
                    current.update(inst.defined_vars)

                if current != self.must_out[b.id]:
                    self.must_out[b.id] = current
                    changed = True

        # Iterate MAY-initialized (possible assignment - union meet)
        changed = True
        iterations = 0
        while changed and iterations < max_iters:
            changed = False
            iterations += 1

            for b in all_blocks:
                if not b.is_reachable and not b.is_entry:
                    continue

                if not b.is_entry:
                    new_may_in = set()
                    for p in b.predecessors:
                        if p.is_reachable:
                            new_may_in.update(self.may_out[p.id])

                    if new_may_in != self.may_in[b.id]:
                        self.may_in[b.id] = new_may_in
                        changed = True

                cur_may = set(self.may_in[b.id])
                for inst in b.instructions:
                    cur_may.update(inst.defined_vars)

                if cur_may != self.may_out[b.id]:
                    self.may_out[b.id] = cur_may
                    changed = True

        # Annotate blocks for UI inspection
        for b in all_blocks:
            b.in_set = set(self.must_in.get(b.id, set()))
            b.out_set = set(self.must_out.get(b.id, set()))

    def _lookup_symbol(self, name: str) -> Optional[Symbol]:
        if self.cfg.scope is not None:
            found = self.cfg.scope.lookup(name)
            if found is not None:
                return found
        return self.symbol_table.lookup(name)

    def _check_uninitialized_reads(self):
        """Scans instructions within reachable blocks to check for reads before initialization."""
        reported_warnings: Set[Tuple[str, int]] = set()

        for b in self.cfg.blocks:
            if not b.is_reachable:
                continue

            current_must = set(self.must_in.get(b.id, set()))
            current_may = set(self.may_in.get(b.id, set()))

            for inst in b.instructions:
                # Check all used variables
                for var_name in inst.used_vars:
                    if hasattr(inst, "used_symbols") and var_name in inst.used_symbols:
                        sym = inst.used_symbols[var_name]
                    else:
                        sym = self._lookup_symbol(var_name)

                    # Only check declared variables (ignore undeclared, functions, and parameters initialized on call)
                    if sym is None or sym.kind in (SymbolKind.FUNCTION, SymbolKind.PARAMETER):
                        continue

                    loc = inst.range.start if inst.range else SourceLocation(1, 1)
                    key = (var_name, loc.line)

                    if var_name not in current_must:
                        if var_name not in current_may:
                            # Uninitialized on ALL reaching paths
                            if key not in reported_warnings:
                                reported_warnings.add(key)
                                self.diagnostics.append(Diagnostic(
                                    severity=Severity.ERROR,
                                    category=DiagnosticCategory.INITIALIZATION,
                                    code="INIT-001",
                                    message=f"Variable '{var_name}' is used before initialization",
                                    location=loc,
                                    range=inst.range,
                                    suggestion=f"Initialize variable '{var_name}' with a value before use"
                                ))
                        else:
                            # Initialized on SOME paths but not all
                            if key not in reported_warnings:
                                reported_warnings.add(key)
                                self.diagnostics.append(Diagnostic(
                                    severity=Severity.WARNING,
                                    category=DiagnosticCategory.INITIALIZATION,
                                    code="INIT-002",
                                    message=f"Variable '{var_name}' may be used before initialization",
                                    location=loc,
                                    range=inst.range,
                                    suggestion=f"Ensure '{var_name}' is assigned on all execution paths before this point"
                                ))

                # Apply definitions
                current_must.update(inst.defined_vars)
                current_may.update(inst.defined_vars)
