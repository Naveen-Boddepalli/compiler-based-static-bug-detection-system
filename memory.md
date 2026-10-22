# Project Memory: Compiler-Based Static Code Analysis and Bug Detection System

This document maintains a chronological record of architectural decisions, implementation choices, bug detection rules, and project milestones.

## Fundamental Guidelines
- Domain: Compiler Design and Static Program Analysis.
- Target: Defined C-like language subset.
- Core Principle: Detect programming defects and safety vulnerabilities without executing the program.
- System Philosophy: High-precision engineering tool, focused and professional.
- Strict Constraints:
  - Zero emojis across all source code, UI, documentation, commit messages, and reports.
  - Distinct, professional developer workbench UI (not a generic AI template).
  - Native dual-mode support (Light and Dark themes) with persistent storage.
  - Granular, atomic git commits for each milestone.

## Architectural Decisions

### 1. Zero External Dependency Strategy
- Choice: Standard Library Python 3.
- Rationale: The core analysis pipeline (lexer, recursive descent parser, symbol table, CFG builder, data-flow solver, bug detectors) and the HTTP server are implemented using only the Python standard library. This prevents environment conflicts, brittle pip installations, and ensures fast, deterministic compilation passes (< 1ms per analysis).

### 2. Handcrafted Recursive Descent Parser
- Choice: Handcrafted recursive descent parser with operator precedence.
- Rationale: Provides exact source location coordinates (line and column numbers) for every AST node, clean syntax error recovery via synchronization tokens, and typed AST nodes with visitor pattern support.

### 3. Hierarchical Scoped Symbol Table
- Choice: Scoped symbol hierarchy with parent and child links.
- Rationale: Accurately reflects lexical scoping, function parameter scope, block nesting, identifier shadowing, and detects duplicate declarations in the same scope versus valid declarations across different scopes.

### 4. Control Flow Graph & Basic Blocks
- Choice: Linearized basic blocks with explicit edge types (Fallthrough, True Branch, False Branch, Jump, Return).
- Rationale: Enables path reachability analysis (discovering unreachable dead code) and provides the structural substrate for data-flow analysis.

### 5. Forward Data-Flow Definite Assignment Analysis
- Choice: Meet-over-all-paths forward data-flow analysis with lattice top initialization.
- Rationale: Distinguishes between definite uninitialized reads (uninitialized on ALL execution paths) and possible uninitialized reads (initialized only on some branches), matching standard compiler diagnostics.

### 6. Interactive Developer Workbench UI
- Choice: High-density developer studio layout with split editor and tabbed inspector.
- Rationale: Replaces generic AI card layouts with a precision engineering layout inspired by tools like Compiler Explorer (Godbolt) and IDE inspection windows. Features real-time line gutter, tab key indentation, vector SVG rendering for CFGs, interactive AST trees, and a persistent dark/light theme switch.

### 7. Dual Execution Architecture (Local REST & In-Browser WebAssembly)
- Choice: Support both Python HTTP server execution and client-side Pyodide WebAssembly.
- Rationale: While running locally via server.py provides lightning-fast (< 1ms) execution, deploying to GitHub Pages requires serverless static hosting. By packaging the zero-dependency Python compiler into a tiny (39.6 KB) zip archive executed via Pyodide WebAssembly, the complete analyzer (AST, CFG, Data-Flow, Detectors) runs natively client-side in the browser on GitHub Pages without requiring any external backend server.

## Bug and Defect Catalog
- Semantic:
  - SEM-001: Void variable declaration
  - SEM-002: Variable redeclaration in same scope
  - SEM-003: Initialization type mismatch
  - SEM-004: Identifier redeclared as function
  - SEM-005: Function redefinition
  - SEM-006: Parameter cannot have void type
  - SEM-007: Duplicate parameter name
  - SEM-008: Void condition in if statement
  - SEM-009: Void condition in while statement
  - SEM-010: Void condition in for statement
  - SEM-011: Return outside function
  - SEM-012: Missing return value in non-void function
  - SEM-013: Void function returning a value
  - SEM-014: Return type mismatch
  - SEM-015: Break outside loop
  - SEM-016: Continue outside loop
  - SEM-020: Undeclared variable access
  - SEM-021: Non-variable operand in increment/decrement
  - SEM-022: Non-numeric operand for unary operator
  - SEM-023: Invalid operands for binary operator
  - SEM-024: Incompatible assignment types
  - SEM-025: Call to undeclared function
  - SEM-026: Called object is not a function
  - SEM-027: Function call argument count mismatch
  - SEM-028: Argument type mismatch in function call
- Initialization:
  - INIT-001: Variable used before initialization (all reaching paths)
  - INIT-002: Variable may be used before initialization (some paths)
  - INIT-003: Variable declared but never used
  - INIT-004: Function parameter never used in body
- Control Flow:
  - CFG-001: Unreachable code detected after unconditional return or jump
  - CFG-002: While loop condition is constant false (0); body never executes
  - CFG-003: Infinite loop without exit condition
  - CFG-004: If condition is constant false; then branch is dead code
  - CFG-005: If condition is constant true; else branch is dead code
- Safety:
  - SAFE-001: Division by constant zero (direct or propagated)
  - SAFE-002: Modulo by constant zero (direct or propagated)

## Verification and Milestones
- 2026-10-20: Git initialized on main branch.
- 2026-10-20: Common diagnostics and source location tracking implemented.
- 2026-10-20: Lexical analyzer completed with full token range tracking and comments support.
- 2026-10-20: AST hierarchy and recursive descent parser completed.
- 2026-10-20: Scoped symbol table and semantic analyzer completed.
- 2026-10-20: Control Flow Graph builder, basic block model, and data-flow analysis completed.
- 2026-10-20: Detectors for initialization, control-flow, and safety completed with constant propagation.
- 2026-10-20: CLI utility and automated test suite completed (all unit and integration tests passing).
- 2026-10-20: Web workbench interface created with light/dark theme, interactive SVG CFG visualizer, AST tree inspector, and export dialog.
- 2026-10-20: Curated C language presets added and verified against Review 1 specification.
- 2026-10-21: Repository pushed and synced with GitHub remote origin at https://github.com/Naveen-Boddepalli/compiler-based-static-bug-detection-system.git.
- 2026-10-21: Top-level snippet parsing implemented to seamlessly evaluate raw C statements (Slide 08 specification) without requiring explicit main() boilerplate.
- 2026-10-21: Parser error recovery hardened against malformed tokens and cascade diagnostics using synthetic typed tokens and clean statement synchronization.
- 2026-10-21: Semantic and initialization detectors hardened to ignore synthetic parser recovery tokens.
- 2026-10-21: Server socket reuse (SO_REUSEADDR) and auto-increment port fallback implemented for presentation reliability.
- 2026-10-21: Developer workbench UI polished with safe SVG viewport alignment and backdrop click dismissal.
- 2026-10-21: Automated test suite expanded to 18 unit and integration tests (100% pass rate in < 0.005s).
- 2026-10-21: Zero-emoji constraint validated across 100% of repository files.
- 2026-10-22: GitHub Actions CI/CD workflow created (.github/workflows/deploy.yml) for automated testing, emoji auditing, artifact building, and GitHub Pages deployment.
- 2026-10-22: Client-side Pyodide WebAssembly runner and static asset packaging implemented in web/app.js and build_dist.py.
- 2026-10-22: Dynamic static asset routing added to server.py and real-time engine mode indicator added to workbench header.
- 2026-10-22: Fixed Python 3.11 backward compatibility in cfg_visualizer.py where f-string expressions containing backslashes caused CI test import failures.
