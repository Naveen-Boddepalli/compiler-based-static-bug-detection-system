# Compiler-Based Static Code Analysis and Bug Detection System

A deterministic, compiler-based static code analysis system for a C-like programming language subset. The system uses classical compiler construction principles (Lexical Analysis, Recursive Descent Parsing, Abstract Syntax Tree generation, Scoped Symbol Tables, Control Flow Graphs, and Forward Data-Flow Analysis) to identify defects, safety risks, and code quality issues without executing the target program.

---

## 1. Objectives and Fundamentals

Potential programming defects frequently escape initial review and remain undetected until execution, testing, or production. This system applies compiler frontend and intermediate representation techniques to catch issues at development time:

- Analyze Without Execution: Evaluate syntactic, semantic, and path-sensitive flow properties purely from source-level structures.
- Practical Compiler Pipeline: Implement an end-to-end compiler pipeline (Lexer -> Parser -> AST -> Semantic Analysis -> CFG -> Data Flow -> Detectors) rather than disconnected exercises.
- Focused and Professional Interface: Provide both a command-line interface for automated testing and CI/CD, and an interactive developer workbench with light and dark theme support.

---

## 2. Language Subset Grammar Supported

The analyzer supports a robust subset of C:

- Types: `int`, `float`, `char`, `bool`, `void`
- Variable Declarations: Single and multi-variable declarations with optional initializers (`int a, b = 10, c;`)
- Functions: Return types, named parameters, function prototypes, and function definition bodies
- Control Flow: `if`, `if-else`, `while`, `for`, `return`, `break`, `continue`, and nested blocks `{ ... }`
- Expressions and Operators:
  - Arithmetic: `+`, `-`, `*`, `/`, `%`
  - Assignment and Compound: `=`, `+=`, `-=`, `*=`, `/=`, `%=`
  - Relational and Equality: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Logical: `&&`, `||`, `!`
  - Unary: `-`, `+`, `!`, `++`, `--` (prefix and postfix)
  - Function calls and grouped parentheses `(expr)`
  - Comments: Single-line (`// ...`) and multi-line (`/* ... */`)

---

## 3. Bug and Vulnerability Detection Coverage

| Category | Rule Code | Severity | Description |
|---|---|---|---|
| Semantic | SEM-001 | ERROR | Void variable declaration |
| Semantic | SEM-002 | ERROR | Variable redeclaration in same scope |
| Semantic | SEM-003 | ERROR | Initialization type mismatch |
| Semantic | SEM-005 | ERROR | Function redefinition |
| Semantic | SEM-012 | ERROR | Missing return value in non-void function |
| Semantic | SEM-013 | ERROR | Void function returning a value |
| Semantic | SEM-014 | ERROR | Return type mismatch |
| Semantic | SEM-015 | ERROR | Break statement outside of loop |
| Semantic | SEM-016 | ERROR | Continue statement outside of loop |
| Semantic | SEM-020 | ERROR | Undeclared variable access |
| Semantic | SEM-023 | ERROR | Invalid operand types for binary operator |
| Semantic | SEM-025 | ERROR | Call to undeclared function |
| Semantic | SEM-027 | ERROR | Function call argument count mismatch |
| Semantic | SEM-028 | ERROR | Function call parameter type mismatch |
| Initialization | INIT-001 | ERROR | Variable used before initialization (all execution paths) |
| Initialization | INIT-002 | WARNING | Variable may be used before initialization (some paths) |
| Initialization | INIT-003 | WARNING | Declared variable never used |
| Initialization | INIT-004 | INFO | Unused function parameter |
| Control Flow | CFG-001 | WARNING | Unreachable code detected after unconditional return/break |
| Control Flow | CFG-002 | WARNING | While loop condition is constant false (0); loop body never executes |
| Control Flow | CFG-003 | WARNING | Infinite loop detected without exit condition |
| Control Flow | CFG-004 | WARNING | If condition is constant false; then branch is dead code |
| Control Flow | CFG-005 | WARNING | If condition is constant true; else branch is dead code |
| Safety | SAFE-001 | ERROR | Division by constant zero (direct or propagated) |
| Safety | SAFE-002 | ERROR | Modulo by constant zero (direct or propagated) |

---

## 4. Architecture and Pipeline

```
  Source Code (.c)
         |
         v
    [ Lexer ]  ---------------> Token Stream (with line:column tracking)
         |
         v
    [ Parser ] ---------------> Abstract Syntax Tree (AST)
         |
         v
[ Semantic Analyzer ] --------> Scoped Symbol Table Hierarchy
         |
         v
  [ CFG Builder ] ------------> Basic Blocks & Control Flow Graph
         |
         v
[ Data-Flow Analyzer ] -------> Definite Assignment (Must-In / Must-Out)
         |
         v
  [ Bug Detectors ] ----------> Semantic, Initialization, Flow, Safety Passes
         |
         v
 [ Analysis Report ] ---------> Diagnostics, Metrics, Graphviz DOT & SVG
```

---

## 5. Getting Started

### Prerequisites
- Python 3.8+ (standard library only; no external package dependencies required)
- Modern web browser (for the interactive workbench)

### Running via Command-Line Interface (CLI)
Analyze any C-like source file directly:
```bash
python3 cli.py samples/review1_sample.c
```

Output formatted JSON report:
```bash
python3 cli.py --json samples/review1_sample.c
```

Export Graphviz DOT control flow graphs:
```bash
python3 cli.py --dot samples/review1_sample.c
```

Run in check-only mode (returns non-zero exit code if errors exist, ideal for CI/CD):
```bash
python3 cli.py --check-only samples/review1_sample.c
```

### Running the Interactive Web Workbench
Start the local server:
```bash
python3 server.py 8000
```
Then navigate to:
```
http://127.0.0.1:8000/
```

Features of the Workbench:
- Source Editor: Real-time line numbering, cursor position display, Tab indentation support (4 spaces), and quick preset loader.
- Diagnostics View: High-density findings table with severity indicators, rule codes, location jumping, and contextual code snippets.
- Control Flow Graph: Interactive vector SVG diagrams with Basic Blocks, true/false branch annotations, and unreachable blocks highlighted.
- Symbol Table Inspector: Hierarchical view of scopes, symbols, declared lines, initialization states, and usage counts.
- AST Inspector: Collapsible and expandable syntax tree with node attributes.
- Token Stream Viewer: Complete list of token types, lexemes, and coordinates.
- Light and Dark Theme: Persistent theme toggle tailored for developer comfort.
- Export Dialog: Download diagnostic reports in formatted text (.txt) or JSON (.json) formats.

---

## 6. Running Tests

Execute the unit and integration test suite:
```bash
python3 -m unittest discover -s tests -v
```

---

## 7. Continuous Integration & GitHub Pages Deployment

The repository includes an automated GitHub Actions CI/CD pipeline (`.github/workflows/deploy.yml`) that triggers on every push to `main` and on manual dispatch:

1. **Automated Testing:** Executes the full unit and integration test suite.
2. **Policy Enforcement:** Enforces the zero-emoji invariant and format standards across 100% of repository files.
3. **Static Distribution Packaging:** Executes `build_dist.py` to package `static_analyzer.zip` and `samples.json` into the production `dist/` bundle with `.nojekyll`.
4. **Automated GitHub Pages Deployment:** Deploys the web workbench directly to GitHub Pages with in-browser WebAssembly (Pyodide) support for 100% serverless execution.

### Enabling GitHub Pages
1. Go to repository **Settings** -> **Pages**.
2. Under **Build and deployment** -> **Source**, select **GitHub Actions**.
3. Pushes to `main` will build and publish the workbench to `https://<username>.github.io/<repo-name>/`.

---

## 8. Project Structure

```
compiler-based-static-but--detention-system/
|-- .github/
|   `-- workflows/
|       `-- deploy.yml              # GitHub Actions CI/CD pipeline for Pages
|-- build_dist.py                   # Packaging script for static distribution
|-- cli.py                          # Command-line interface
|-- server.py                       # HTTP REST server and static host
|-- memory.md                       # Project decisions and change history
|-- README.md                       # Documentation
|-- samples/                        # Curated C test programs
|   |-- review1_sample.c
|   |-- slide08_snippet.c
|   |-- division_by_zero.c
|   |-- dead_code_and_loops.c
|   |-- scope_and_types.c
|   `-- clean_program.c
|-- static_analyzer/                # Core compiler analysis package
|   |-- common/                     # Source locations, ranges, diagnostics
|   |-- lexer/                      # Tokenizer and token definitions
|   |-- parser/                     # Recursive descent parser and AST nodes
|   |-- semantics/                  # Type system, scopes, symbol tables
|   |-- cfg/                        # Basic blocks, CFG builder, data-flow, SVG
|   |-- detectors/                  # Bug detectors (Semantic, Init, CFG, Safety)
|   `-- pipeline.py                 # Central orchestrator
|-- tests/                          # Automated unit and integration tests
`-- web/                            # Interactive developer workbench UI
    |-- index.html
    |-- style.css
    `-- app.js
```
