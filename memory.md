# Project Memory: Compiler-Based Static Code Analysis and Bug Detection System

This file documents the architectural decisions, design choices, scope definitions, and change history for the project.

## Project Fundamentals
- Course / Domain: Compiler Design / Program Analysis
- Target: C-like language subset
- Goal: Early detection of programming defects and vulnerabilities using classical compiler structures (Lexer, Parser, AST, Scoped Symbol Table, Control Flow Graph, and Data-Flow Analysis) without program execution.
- Operational Rules:
  - No emojis anywhere in source code, UI, documentation, commit messages, or reports.
  - Unique, focused, professional developer workbench UI (not a generic AI template).
  - High-precision compiler analysis pipeline.
  - Support for both light and dark modes with persistent user preference.
  - Incremental git commits for every key module.

## Architecture Decisions
1. Implementation Language: Python 3 (standard library based)
   - Decision: Use pure Python standard library for the core analysis pipeline and lightweight HTTP service.
   - Rationale: Eliminates brittle external package dependencies, runs consistently across platforms, facilitates full deterministic control over AST structures and graph algorithms, and allows clean recursive-descent parsing with fine-grained error reporting.
2. Parser Strategy: Handcrafted Recursive Descent with Precedence Climbing
   - Decision: Implement a dedicated recursive-descent parser with source position tracking (line and column coordinates).
   - Rationale: Handcrafted recursive descent provides precise source spans, excellent syntax error recovery, and direct construction of typed AST nodes without relying on heavy external generator runtimes.
3. Symbol Table Architecture: Lexical Scope Tree
   - Decision: Hierarchical symbol tables with parent pointers for nested blocks and functions.
   - Rationale: Direct representation of lexical scope rules, shadowing, and resolution of identifiers across nested statement blocks.
4. Control Flow Graph (CFG) Strategy:
   - Decision: Basic blocks with explicit control-flow edges (Fallthrough, Conditional True, Conditional False, Jump, Return).
   - Rationale: Enables path-sensitive analysis, dead code detection, and data-flow algorithms (definite assignment tracking).
5. Data-Flow Analysis:
   - Decision: Forward data-flow analysis on CFG for tracking variable definition and use states.
   - Rationale: Accurately discovers reads of uninitialized variables across complex branches and loops.

## Change Log
- 2026-10-20: Project initialized with git repository on main branch.
- 2026-10-20: Memory file established with core design specifications.
