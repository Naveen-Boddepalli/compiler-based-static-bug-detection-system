/**
 * Static Code Analysis & Bug Detection Workbench - Controller
 * Strictly no emojis anywhere in code or user-visible text.
 */

(function () {
    "use strict";

    // Application State
    const state = {
        theme: localStorage.getItem("sca_theme") || "dark",
        samples: {},
        activeSampleKey: "",
        analysisResult: null,
        activeTab: "tab-diagnostics",
        filterSeverity: "ALL",
        filterCategory: "ALL",
        activeCfgView: "svg",
        selectedFunctionIndex: 0
    };

    // DOM Elements
    const elements = {
        html: document.documentElement,
        btnTheme: document.getElementById("btn-theme"),
        sampleSelect: document.getElementById("sample-select"),
        btnAnalyze: document.getElementById("btn-analyze"),
        btnExport: document.getElementById("btn-export"),
        codeInput: document.getElementById("code-input"),
        editorGutter: document.getElementById("editor-gutter"),
        currentFilename: document.getElementById("current-filename"),
        linesCount: document.getElementById("editor-lines-count"),
        charCount: document.getElementById("editor-char-count"),
        cursorPos: document.getElementById("editor-cursor-pos"),
        btnClearCode: document.getElementById("btn-clear-code"),
        btnResetCode: document.getElementById("btn-reset-code"),

        // Badges
        diagBadge: document.getElementById("diag-badge"),
        cfgBadge: document.getElementById("cfg-badge"),
        symBadge: document.getElementById("sym-badge"),
        tokensBadge: document.getElementById("tokens-badge"),

        // Metrics
        metricErrors: document.getElementById("metric-errors-count"),
        metricWarnings: document.getElementById("metric-warnings-count"),
        metricInfo: document.getElementById("metric-info-count"),
        metricLatency: document.getElementById("metric-latency"),

        // Tab Panels & Lists
        tabButtons: document.querySelectorAll(".tab-btn"),
        tabPanes: document.querySelectorAll(".tab-pane"),
        diagnosticsList: document.getElementById("diagnostics-list"),
        filterSeverityPills: document.querySelectorAll("[data-filter-sev]"),
        filterCategoryPills: document.querySelectorAll("[data-filter-cat]"),

        // CFG Elements
        cfgFnSelect: document.getElementById("cfg-fn-select"),
        cfgViewPills: document.querySelectorAll("[data-cfg-view]"),
        cfgViewSvg: document.getElementById("cfg-view-svg"),
        cfgViewTable: document.getElementById("cfg-view-table"),
        cfgViewDot: document.getElementById("cfg-view-dot"),
        cfgSvgContainer: document.getElementById("cfg-svg-container"),
        cfgBlocksTbody: document.getElementById("cfg-blocks-tbody"),
        cfgDotCode: document.getElementById("cfg-dot-code"),
        btnCopyDot: document.getElementById("btn-copy-dot"),

        // Symbol Table
        symScopesCount: document.getElementById("sym-scopes-count"),
        symTotalCount: document.getElementById("sym-total-count"),
        symbolsTbody: document.getElementById("symbols-tbody"),

        // AST
        astNodesCount: document.getElementById("ast-nodes-count"),
        astTreeContainer: document.getElementById("ast-tree-container"),
        btnExpandAst: document.getElementById("btn-expand-ast"),
        btnCollapseAst: document.getElementById("btn-collapse-ast"),

        // Tokens
        tokensTotalCount: document.getElementById("tokens-total-count"),
        tokensTbody: document.getElementById("tokens-tbody"),

        // Export Modal
        exportDialog: document.getElementById("export-dialog"),
        btnCloseExport: document.getElementById("btn-close-export"),
        btnDownloadTxt: document.getElementById("btn-download-txt"),
        btnDownloadJson: document.getElementById("btn-download-json"),
        btnCopyReport: document.getElementById("btn-copy-report"),
        exportPreviewText: document.getElementById("export-preview-text"),

        // Engine Status
        engineBadge: document.getElementById("engine-status-badge"),
        engineStatusText: document.getElementById("engine-status-text")
    };

    // Engine State
    const engineState = {
        mode: "detecting",
        pyodide: null,
        pyodidePromise: null,
        statusText: "Engine: Initializing..."
    };

    function setEngineMode(mode, text) {
        engineState.mode = mode;
        engineState.statusText = text;
        if (elements.engineStatusText) {
            elements.engineStatusText.textContent = text;
        }
        if (elements.engineBadge) {
            elements.engineBadge.className = "engine-badge " + (
                mode === "server" ? "engine-local" :
                mode === "wasm" ? "engine-wasm" :
                mode === "loading" ? "engine-loading" :
                mode === "error" ? "engine-error" : ""
            );
        }
    }

    async function ensurePyodideReady() {
        if (engineState.pyodide) return engineState.pyodide;
        if (engineState.pyodidePromise) return engineState.pyodidePromise;

        engineState.pyodidePromise = (async () => {
            let retries = 0;
            while (typeof loadPyodide === "undefined" && retries < 25) {
                await new Promise(r => setTimeout(r, 200));
                retries++;
            }
            if (typeof loadPyodide === "undefined") {
                throw new Error("Pyodide WebAssembly library is not accessible");
            }

            setEngineMode("loading", "Engine: Loading Python Wasm...");
            const pyodide = await loadPyodide({
                indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/"
            });

            setEngineMode("loading", "Engine: Unpacking Analyzer...");
            const zipResp = await fetch("static_analyzer.zip");
            if (!zipResp.ok) {
                throw new Error(`Failed to load static_analyzer.zip: HTTP ${zipResp.status}`);
            }
            const zipBuf = await zipResp.arrayBuffer();
            pyodide.FS.writeFile("static_analyzer.zip", new Uint8Array(zipBuf));

            await pyodide.runPythonAsync(`
import sys
if "static_analyzer.zip" not in sys.path:
    sys.path.insert(0, "static_analyzer.zip")
from static_analyzer.pipeline import AnalyzerPipeline
import json

_pipeline = AnalyzerPipeline()

def analyze_c_source(code, filename):
    result = _pipeline.analyze(code, filename=filename)
    return json.dumps(result.to_dict())
`);
            engineState.pyodide = pyodide;
            setEngineMode("wasm", "Engine: WebAssembly (Wasm)");
            return pyodide;
        })();

        return engineState.pyodidePromise;
    }

    async function initEngine() {
        const isLocalHost = window.location.hostname === "localhost" ||
                            window.location.hostname === "127.0.0.1" ||
                            (window.location.port && window.location.port !== "80" && window.location.port !== "443" && !window.location.hostname.includes("github.io"));

        if (isLocalHost) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 1200);
                const resp = await fetch("/api/health", { signal: controller.signal });
                clearTimeout(timeoutId);
                if (resp.ok) {
                    setEngineMode("server", "Engine: Local Server");
                    return;
                }
            } catch (err) {
                // local server not responding, switch to wasm
            }
        }

        setEngineMode("loading", "Engine: Initializing Wasm...");
        try {
            await ensurePyodideReady();
            setEngineMode("wasm", "Engine: WebAssembly (Wasm)");
        } catch (err) {
            console.warn("Pyodide background pre-load error:", err);
            setEngineMode("error", "Engine: Ready on Demand");
        }
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    function init() {
        applyTheme(state.theme);
        setupEventListeners();
        loadSamplesList();
        initEngine();
        updateGutter();
        updateCursorPosition();
    }

    // =========================================================================
    // Theme Management
    // =========================================================================

    function applyTheme(themeName) {
        state.theme = themeName;
        elements.html.setAttribute("data-theme", themeName);
        elements.btnTheme.textContent = themeName === "dark" ? "Theme: Dark" : "Theme: Light";
        localStorage.setItem("sca_theme", themeName);

        // Re-render SVG if analysis result is available
        if (state.analysisResult && state.analysisResult.cfgs.length > 0) {
            renderCurrentCfg();
        }
    }

    function toggleTheme() {
        applyTheme(state.theme === "dark" ? "light" : "dark");
    }

    // =========================================================================
    // Editor Mechanics (Line Numbers, Cursor, Tab Support)
    // =========================================================================

    function updateGutter() {
        const text = elements.codeInput.value;
        const lineCount = text.split("\n").length;
        let gutterNumbers = [];
        for (let i = 1; i <= lineCount; i++) {
            gutterNumbers.push(i);
        }
        elements.editorGutter.textContent = gutterNumbers.join("\n");
        elements.linesCount.textContent = `${lineCount} line${lineCount !== 1 ? "s" : ""}`;
        elements.charCount.textContent = `${text.length} chars`;
    }

    function updateCursorPosition() {
        const textarea = elements.codeInput;
        const pos = textarea.selectionStart;
        const textToPos = textarea.value.substring(0, pos);
        const lines = textToPos.split("\n");
        const lineNum = lines.length;
        const colNum = lines[lines.length - 1].length + 1;
        elements.cursorPos.textContent = `Ln ${lineNum}, Col ${colNum}`;
    }

    function syncGutterScroll() {
        elements.editorGutter.scrollTop = elements.codeInput.scrollTop;
    }

    function jumpToLine(lineNumber) {
        const lines = elements.codeInput.value.split("\n");
        let charIndex = 0;
        for (let i = 0; i < lineNumber - 1 && i < lines.length; i++) {
            charIndex += lines[i].length + 1;
        }

        elements.codeInput.focus();
        elements.codeInput.setSelectionRange(charIndex, charIndex + (lines[lineNumber - 1] ? lines[lineNumber - 1].length : 0));

        // Scroll into view
        const approxLineHeight = 20;
        elements.codeInput.scrollTop = Math.max(0, (lineNumber - 4) * approxLineHeight);
        updateCursorPosition();
    }

    // =========================================================================
    // Samples Loading
    // =========================================================================

    async function loadSamplesList() {
        try {
            const resp = await fetch("/api/samples");
            if (resp.ok) {
                const data = await resp.json();
                if (data.samples && Object.keys(data.samples).length > 0) {
                    state.samples = data.samples;
                    populateSampleSelect();
                    return;
                }
            }
        } catch (err) {
            // API endpoint not available on static host
        }

        try {
            const staticResp = await fetch("samples.json");
            if (staticResp.ok) {
                const data = await staticResp.json();
                if (data.samples && Object.keys(data.samples).length > 0) {
                    state.samples = data.samples;
                    populateSampleSelect();
                    return;
                }
            }
        } catch (err) {
            // Static file not accessible
        }

        useFallbackSamples();
    }

    function populateSampleSelect() {
        elements.sampleSelect.innerHTML = '<option value="">-- Load Preset --</option>';
        const titles = {
            "review1_sample.c": "Review 1 Spec (With main Function)",
            "slide08_snippet.c": "Slide 08 Exact Snippet (Direct Code)",
            "division_by_zero.c": "Division by Constant Zero & Modulo",
            "dead_code_and_loops.c": "Dead Code & Loop Defects",
            "scope_and_types.c": "Scope Violations & Redeclarations",
            "clean_program.c": "Clean Factorial (Passing 0 Issues)"
        };

        for (const [filename, code] of Object.entries(state.samples)) {
            const opt = document.createElement("option");
            opt.value = filename;
            opt.textContent = titles[filename] || filename;
            elements.sampleSelect.appendChild(opt);
        }

        // Auto-select Review 1 sample by default
        if (state.samples["review1_sample.c"]) {
            loadSample("review1_sample.c");
        }
    }

    function useFallbackSamples() {
        state.samples = {
            "review1_sample.c": "// Review 1 Specification Test Case\n// Demonstrates uninitialized variable access and undeclared variable use.\nint main() {\n    int x;\n    if (x > 10) {\n        return 0;\n    }\n    y = x + 5;\n    return 0;\n}\n",
            "slide08_snippet.c": "// Slide 08 Exact Proposal Code Snippet\n// Demonstrates uninitialized variable access and undeclared variable without wrapping in main().\nint x;\nif (x > 10) {\n    return 0;\n}\ny = x + 5;\n",
            "division_by_zero.c": "// Division by Zero & Safety Defects\n// Demonstrates constant division/modulo by zero and constant propagation.\nint calculate(int base) {\n    int zero_val = 0;\n    int direct_div = base / 0;\n    int propagated_div = base / zero_val;\n    int folded_div = base / (10 - 10);\n    int zero_mod = base % 0;\n    return direct_div + propagated_div + folded_div + zero_mod;\n}\n",
            "dead_code_and_loops.c": "// Dead Code & Control-Flow Defects\n// Demonstrates statements after unconditional return, dead loop conditions, and unused variables.\nint process_values(int limit) {\n    int unused_cache = 100;\n\n    // Dead loop: condition is constant false (0)\n    while (0) {\n        int dead_iteration = 1;\n    }\n\n    if (limit > 50) {\n        return 1;\n        // Unreachable statement after unconditional return\n        int unreachable_after_return = limit * 2;\n    }\n\n    return 0;\n}\n",
            "scope_and_types.c": "// Scope & Semantic Defects\n// Demonstrates duplicate declarations in the same scope, scope leakage, and void type misuse.\nint compute_scope(int val) {\n    int counter = 10;\n    // Duplicate declaration in same scope\n    int counter = 20;\n\n    if (val > 0) {\n        int inner_scoped_var = 50;\n    }\n\n    // Scope violation: inner_scoped_var is not accessible in outer scope\n    int total = inner_scoped_var + counter;\n\n    return total;\n}\n",
            "clean_program.c": "// Clean, Well-Formed Program (0 Errors, 0 Warnings)\n// Demonstrates correct static analysis passing across functions, loops, and flow.\nint factorial(int n) {\n    int result = 1;\n    int i = 1;\n    while (i <= n) {\n        result = result * i;\n        i++;\n    }\n    return result;\n}\n\nint main() {\n    int input = 5;\n    int output = factorial(input);\n    return output;\n}\n"
        };
        populateSampleSelect();
    }

    function loadSample(filename) {
        if (state.samples[filename]) {
            state.activeSampleKey = filename;
            elements.sampleSelect.value = filename;
            elements.codeInput.value = state.samples[filename];
            elements.currentFilename.textContent = filename;
            updateGutter();
            updateCursorPosition();
            runAnalysis();
        }
    }

    // =========================================================================
    // Core Static Analysis Request
    // =========================================================================

    async function runAnalysis() {
        const code = elements.codeInput.value;
        const filename = elements.currentFilename.textContent || "input.c";

        elements.btnAnalyze.classList.add("loading");
        elements.btnAnalyze.disabled = true;

        try {
            let result = null;

            if (engineState.mode === "server") {
                try {
                    const resp = await fetch("/api/analyze", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ code: code, filename: filename })
                    });
                    if (resp.ok) {
                        result = await resp.json();
                    } else {
                        const errData = await resp.json().catch(() => ({}));
                        throw new Error(errData.error || `Server responded with HTTP ${resp.status}`);
                    }
                } catch (netErr) {
                    console.warn("Local server call failed, attempting WebAssembly execution...", netErr);
                    setEngineMode("loading", "Engine: Switching to Wasm...");
                    const pyodide = await ensurePyodideReady();
                    setEngineMode("wasm", "Engine: WebAssembly (Wasm)");
                    const startTime = performance.now();
                    const runFn = pyodide.globals.get("analyze_c_source");
                    const jsonStr = runFn(code, filename);
                    const elapsedMs = performance.now() - startTime;
                    result = JSON.parse(jsonStr);
                    if (result && result.metrics) {
                        result.metrics.elapsed_ms = Math.round(elapsedMs * 100) / 100;
                    }
                }
            } else {
                // WebAssembly mode (GitHub Pages or static host)
                const pyodide = await ensurePyodideReady();
                setEngineMode("wasm", "Engine: WebAssembly (Wasm)");
                const startTime = performance.now();
                const runFn = pyodide.globals.get("analyze_c_source");
                const jsonStr = runFn(code, filename);
                const elapsedMs = performance.now() - startTime;
                result = JSON.parse(jsonStr);
                if (result && result.metrics) {
                    result.metrics.elapsed_ms = Math.round(elapsedMs * 100) / 100;
                }
            }

            state.analysisResult = result;
            renderAnalysisResult(result);
        } catch (err) {
            renderErrorBanner(err.message || String(err));
        } finally {
            elements.btnAnalyze.classList.remove("loading");
            elements.btnAnalyze.disabled = false;
        }
    }

    // =========================================================================
    // Rendering Analysis Results
    // =========================================================================

    function renderAnalysisResult(res) {
        const m = res.metrics;

        // Update Header Badges
        elements.diagBadge.textContent = (m.total_errors + m.total_warnings + m.total_info).toString();
        elements.cfgBadge.textContent = (res.cfgs || []).length.toString();
        elements.symBadge.textContent = ((res.symbol_table && res.symbol_table.symbols_flat) || []).length.toString();
        elements.tokensBadge.textContent = (res.tokens || []).length.toString();

        // Update Metrics Strip
        elements.metricErrors.textContent = m.total_errors;
        elements.metricWarnings.textContent = m.total_warnings;
        elements.metricInfo.textContent = m.total_info;
        elements.metricLatency.textContent = `${m.elapsed_ms} ms`;

        // Render Tabs Content
        renderDiagnosticsList(res.diagnostics || []);
        renderCfgSection(res.cfgs || []);
        renderSymbolTable(res.symbol_table);
        renderAstTree(res.ast, m.total_ast_nodes);
        renderTokensTable(res.tokens || []);
    }

    function renderErrorBanner(msg) {
        elements.diagnosticsList.innerHTML = `
            <div class="finding-card severity-error">
                <div class="finding-header">
                    <span class="badge-sev">ANALYZER ERROR</span>
                </div>
                <div class="finding-msg">${escapeHtml(msg)}</div>
            </div>
        `;
    }

    // =========================================================================
    // Render Tab 1: Diagnostics
    // =========================================================================

    function renderDiagnosticsList(diagnostics) {
        // Filter diagnostics
        const filtered = diagnostics.filter(d => {
            const matchesSev = (state.filterSeverity === "ALL") || (d.severity === state.filterSeverity);
            const matchesCat = (state.filterCategory === "ALL") || (d.category === state.filterCategory);
            return matchesSev && matchesCat;
        });

        if (filtered.length === 0) {
            if (diagnostics.length === 0) {
                elements.diagnosticsList.innerHTML = `
                    <div class="empty-state">
                        <p class="empty-title">All Static Checks Passed</p>
                        <p class="empty-desc">No syntax, semantic, initialization, control-flow, or safety issues detected in the source code.</p>
                    </div>
                `;
            } else {
                elements.diagnosticsList.innerHTML = `
                    <div class="empty-state">
                        <p class="empty-title">No Findings Match Filter</p>
                        <p class="empty-desc">${diagnostics.length} issue(s) detected under other severity or category criteria.</p>
                    </div>
                `;
            }
            return;
        }

        const cardsHtml = filtered.map(d => {
            const sevClass = `severity-${d.severity.toLowerCase()}`;
            const locText = `Ln ${d.location.line}, Col ${d.location.column}`;

            let suggestionHtml = "";
            if (d.suggestion) {
                suggestionHtml = `<div class="finding-suggestion">Suggestion: ${escapeHtml(d.suggestion)}</div>`;
            }

            // Excerpt snippet
            const snippetHtml = buildSourceSnippet(d.location.line);

            return `
                <div class="finding-card ${sevClass}">
                    <div class="finding-header">
                        <div class="finding-meta">
                            <span class="badge-sev">[${escapeHtml(d.severity)}]</span>
                            <span class="tag-category">${escapeHtml(d.category)}</span>
                            <span class="code-pill">${escapeHtml(d.code)}</span>
                        </div>
                        <button class="loc-btn" data-jump-line="${d.location.line}">${locText}</button>
                    </div>
                    <div class="finding-msg">${escapeHtml(d.message)}</div>
                    ${suggestionHtml}
                    ${snippetHtml}
                </div>
            `;
        }).join("");

        elements.diagnosticsList.innerHTML = cardsHtml;

        // Bind Jump buttons
        elements.diagnosticsList.querySelectorAll("[data-jump-line]").forEach(btn => {
            btn.addEventListener("click", () => {
                const ln = parseInt(btn.getAttribute("data-jump-line"), 10);
                jumpToLine(ln);
            });
        });
    }

    function buildSourceSnippet(lineNum) {
        const lines = elements.codeInput.value.split("\n");
        const start = Math.max(1, lineNum - 1);
        const end = Math.min(lines.length, lineNum + 1);

        let snippetLines = [];
        for (let ln = start; ln <= end; ln++) {
            const rawLine = lines[ln - 1] || "";
            const isTarget = (ln === lineNum);
            const marker = isTarget ? ">" : " ";
            const cls = isTarget ? "snippet-target" : "";
            snippetLines.push(`${marker} ${ln.toString().padStart(3, " ")} | <span class="${cls}">${escapeHtml(rawLine)}</span>`);
        }

        return `<pre class="finding-snippet">${snippetLines.join("\n")}</pre>`;
    }

    // =========================================================================
    // Render Tab 2: Control Flow Graph (CFG)
    // =========================================================================

    function renderCfgSection(cfgs) {
        if (!cfgs || cfgs.length === 0) {
            elements.cfgFnSelect.innerHTML = '<option value="0">No functions defined</option>';
            elements.cfgSvgContainer.innerHTML = '<p class="text-muted">No function definitions found to build CFG.</p>';
            elements.cfgBlocksTbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No CFG basic blocks.</td></tr>';
            elements.cfgDotCode.textContent = "// No CFG available";
            return;
        }

        // Populate Function selector
        elements.cfgFnSelect.innerHTML = cfgs.map((c, idx) => `
            <option value="${idx}" ${idx === state.selectedFunctionIndex ? "selected" : ""}>
                function ${escapeHtml(c.function_name)} (${c.cfg.total_blocks} blocks)
            </option>
        `).join("");

        if (state.selectedFunctionIndex >= cfgs.length) {
            state.selectedFunctionIndex = 0;
        }

        renderCurrentCfg();
    }

    function renderCurrentCfg() {
        if (!state.analysisResult || !state.analysisResult.cfgs || state.analysisResult.cfgs.length === 0) {
            return;
        }

        const artifact = state.analysisResult.cfgs[state.selectedFunctionIndex];
        if (!artifact) return;

        // SVG Render
        const svgCode = state.theme === "dark" ? artifact.svg_dark : artifact.svg_light;
        elements.cfgSvgContainer.innerHTML = svgCode;

        // DOT Render
        elements.cfgDotCode.textContent = artifact.dot;

        // Blocks Table Render
        const blocks = artifact.cfg.blocks || [];
        elements.cfgBlocksTbody.innerHTML = blocks.map(b => {
            const statusLabel = !b.is_reachable && !b.is_exit ? '<span class="badge-sev severity-error">[UNREACHABLE]</span>' :
                                b.is_entry ? '<span class="badge-sev severity-info">[ENTRY]</span>' :
                                b.is_exit ? '<span class="badge-sev severity-warning">[EXIT]</span>' :
                                '<span>Reachable</span>';

            const instList = b.instructions.map(i => escapeHtml(i.text)).join("<br/>") || '<span class="text-muted">(none)</span>';
            const preds = b.predecessor_ids.length > 0 ? b.predecessor_ids.map(id => `B${id}`).join(", ") : '<span class="text-muted">none</span>';
            const succs = b.successor_ids.length > 0 ? b.successor_ids.map(id => `B${id}`).join(", ") : '<span class="text-muted">none</span>';
            const inVars = b.in_vars.length > 0 ? `{${b.in_vars.join(", ")}}` : '<span class="text-muted">{}</span>';
            const outVars = b.out_vars.length > 0 ? `{${b.out_vars.join(", ")}}` : '<span class="text-muted">{}</span>';

            return `
                <tr>
                    <td><strong>B${b.id}</strong></td>
                    <td>${escapeHtml(b.label)}</td>
                    <td>${instList}</td>
                    <td>${preds}</td>
                    <td>${succs}</td>
                    <td>${inVars}</td>
                    <td>${outVars}</td>
                    <td>${statusLabel}</td>
                </tr>
            `;
        }).join("");
    }

    // =========================================================================
    // Render Tab 3: Symbol Table
    // =========================================================================

    function renderSymbolTable(symTable) {
        if (!symTable || !symTable.symbols_flat || symTable.symbols_flat.length === 0) {
            elements.symScopesCount.textContent = "0";
            elements.symTotalCount.textContent = "0";
            elements.symbolsTbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No symbols registered.</td></tr>';
            return;
        }

        elements.symScopesCount.textContent = symTable.total_scopes.toString();
        elements.symTotalCount.textContent = symTable.symbols_flat.length.toString();

        elements.symbolsTbody.innerHTML = symTable.symbols_flat.map(s => {
            const initText = s.is_initialized ? '<span style="color:var(--accent-green);">true</span>' : '<span style="color:var(--accent-red);">false</span>';
            const usedText = s.is_used ? '<span style="color:var(--accent-green);">true</span>' : '<span style="color:var(--accent-amber);">false</span>';

            return `
                <tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td><code>${escapeHtml(s.type)}</code></td>
                    <td><span class="tag-category">${escapeHtml(s.kind)}</span></td>
                    <td>Scope ${s.scope_id}</td>
                    <td><button class="loc-btn" data-jump-line="${s.declared_location.line}">Line ${s.declared_location.line}</button></td>
                    <td>${initText}</td>
                    <td>${usedText}</td>
                    <td>${s.use_count}</td>
                </tr>
            `;
        }).join("");

        elements.symbolsTbody.querySelectorAll("[data-jump-line]").forEach(btn => {
            btn.addEventListener("click", () => {
                const ln = parseInt(btn.getAttribute("data-jump-line"), 10);
                jumpToLine(ln);
            });
        });
    }

    // =========================================================================
    // Render Tab 4: Abstract Syntax Tree (AST)
    // =========================================================================

    function renderAstTree(ast, totalNodes) {
        elements.astNodesCount.textContent = totalNodes.toString();
        if (!ast) {
            elements.astTreeContainer.innerHTML = '<p class="text-muted">No AST generated.</p>';
            return;
        }

        elements.astTreeContainer.innerHTML = buildAstNodeHtml(ast);

        // Bind interactive collapse/expand
        elements.astTreeContainer.querySelectorAll(".tree-node-header").forEach(header => {
            header.addEventListener("click", () => {
                const parent = header.parentElement;
                parent.classList.toggle("collapsed");
                const toggle = header.querySelector(".tree-toggle");
                if (toggle) {
                    toggle.textContent = parent.classList.contains("collapsed") ? "[+]" : "[-]";
                }
            });
        });
    }

    function buildAstNodeHtml(node) {
        if (!node || typeof node !== "object") return "";

        const nodeType = node.node_type || "Node";
        let titleParts = [`<span class="tree-node-type">${escapeHtml(nodeType)}</span>`];

        if (node.name) titleParts.push(`<span class="tree-node-name">name="${escapeHtml(node.name)}"</span>`);
        if (node.operator) titleParts.push(`<span class="tree-node-val">op="${escapeHtml(node.operator)}"</span>`);
        if (node.value !== undefined && node.value !== null) titleParts.push(`<span class="tree-node-val">val=${escapeHtml(String(node.value))}</span>`);
        if (node.range) titleParts.push(`<span class="tree-node-range">[${node.range.start.line}:${node.range.start.column}]</span>`);

        let childrenHtml = [];
        for (const [key, val] of Object.entries(node)) {
            if (["node_type", "range", "name", "operator", "value", "raw"].includes(key)) continue;

            if (Array.isArray(val)) {
                val.forEach(item => {
                    if (item && typeof item === "object") {
                        childrenHtml.push(buildAstNodeHtml(item));
                    }
                });
            } else if (val && typeof val === "object") {
                childrenHtml.push(buildAstNodeHtml(val));
            }
        }

        const hasChildren = childrenHtml.length > 0;
        const toggleStr = hasChildren ? '<span class="tree-toggle">[-]</span>' : '<span class="tree-toggle" style="opacity:0.2;">•</span>';

        return `
            <div class="tree-node">
                <div class="tree-node-header">
                    ${toggleStr}
                    ${titleParts.join(" ")}
                </div>
                ${hasChildren ? `<div class="tree-children">${childrenHtml.join("")}</div>` : ""}
            </div>
        `;
    }

    // =========================================================================
    // Render Tab 5: Tokens
    // =========================================================================

    function renderTokensTable(tokens) {
        elements.tokensTotalCount.textContent = tokens.length.toString();
        if (tokens.length === 0) {
            elements.tokensTbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No tokens generated.</td></tr>';
            return;
        }

        elements.tokensTbody.innerHTML = tokens.map((t, idx) => {
            const valText = t.value !== null ? escapeHtml(String(t.value)) : '<span class="text-muted">-</span>';
            return `
                <tr>
                    <td>${idx + 1}</td>
                    <td><code>${escapeHtml(t.type)}</code></td>
                    <td><strong>${escapeHtml(t.lexeme || "<EOF>")}</strong></td>
                    <td>${valText}</td>
                    <td><button class="loc-btn" data-jump-line="${t.line}">${t.line}:${t.column}</button></td>
                </tr>
            `;
        }).join("");

        elements.tokensTbody.querySelectorAll("[data-jump-line]").forEach(btn => {
            btn.addEventListener("click", () => {
                const ln = parseInt(btn.getAttribute("data-jump-line"), 10);
                jumpToLine(ln);
            });
        });
    }

    // =========================================================================
    // Export Report
    // =========================================================================

    function openExportModal() {
        if (!state.analysisResult) {
            alert("Please execute static analysis first before exporting.");
            return;
        }

        const reportText = buildTextReport(state.analysisResult);
        elements.exportPreviewText.value = reportText;
        elements.exportDialog.showModal();
    }

    function buildTextReport(res) {
        const m = res.metrics;
        const divider = "========================================================================";
        let lines = [
            divider,
            "STATIC CODE ANALYSIS REPORT",
            `File: ${res.filename} (${m.total_lines} lines, ${m.total_tokens} tokens)`,
            `Execution Latency: ${m.elapsed_ms} ms`,
            `Diagnostics: ${m.total_errors} errors, ${m.total_warnings} warnings, ${m.total_info} info notes`,
            divider,
            ""
        ];

        if (res.diagnostics.length === 0) {
            lines.push("Zero defects detected. All static analysis compiler checks passed.");
        } else {
            res.diagnostics.forEach(d => {
                lines.push(`[${d.severity}] [${d.code}] ${d.location.line}:${d.location.column}: ${d.message}`);
                if (d.suggestion) {
                    lines.push(`    Suggestion: ${d.suggestion}`);
                }
                lines.push("------------------------------------------------------------------------");
            });
        }
        return lines.join("\n");
    }

    function downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // =========================================================================
    // Event Listeners Setup
    // =========================================================================

    function setupEventListeners() {
        // Theme button
        elements.btnTheme.addEventListener("click", toggleTheme);

        // Analyze button & Shortcut
        elements.btnAnalyze.addEventListener("click", runAnalysis);

        window.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                runAnalysis();
            }
        });

        // Sample selection
        elements.sampleSelect.addEventListener("change", (e) => {
            if (e.target.value) {
                loadSample(e.target.value);
            }
        });

        // Editor inputs & navigation
        elements.codeInput.addEventListener("input", () => {
            updateGutter();
            updateCursorPosition();
        });

        elements.codeInput.addEventListener("scroll", syncGutterScroll);

        elements.codeInput.addEventListener("keyup", updateCursorPosition);
        elements.codeInput.addEventListener("click", updateCursorPosition);

        // Tab key handling (4 spaces indentation)
        elements.codeInput.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = elements.codeInput.selectionStart;
                const end = elements.codeInput.selectionEnd;
                elements.codeInput.value = elements.codeInput.value.substring(0, start) + "    " + elements.codeInput.value.substring(end);
                elements.codeInput.selectionStart = elements.codeInput.selectionEnd = start + 4;
                updateGutter();
                updateCursorPosition();
            }
        });

        // Clear and Reset buttons
        elements.btnClearCode.addEventListener("click", () => {
            elements.codeInput.value = "";
            updateGutter();
            updateCursorPosition();
        });

        elements.btnResetCode.addEventListener("click", () => {
            if (state.activeSampleKey) {
                loadSample(state.activeSampleKey);
            }
        });

        // Inspector Tabs
        elements.tabButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                state.activeTab = targetTab;

                elements.tabButtons.forEach(b => {
                    const isTarget = b === btn;
                    b.classList.toggle("active", isTarget);
                    b.setAttribute("aria-selected", isTarget ? "true" : "false");
                });

                elements.tabPanes.forEach(pane => {
                    pane.classList.toggle("active", pane.id === targetTab);
                });
            });
        });

        // Severity Filters
        elements.filterSeverityPills.forEach(pill => {
            pill.addEventListener("click", () => {
                elements.filterSeverityPills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                state.filterSeverity = pill.getAttribute("data-filter-sev");
                if (state.analysisResult) {
                    renderDiagnosticsList(state.analysisResult.diagnostics || []);
                }
            });
        });

        // Category Filters
        elements.filterCategoryPills.forEach(pill => {
            pill.addEventListener("click", () => {
                elements.filterCategoryPills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                state.filterCategory = pill.getAttribute("data-filter-cat");
                if (state.analysisResult) {
                    renderDiagnosticsList(state.analysisResult.diagnostics || []);
                }
            });
        });

        // CFG Function Selector
        elements.cfgFnSelect.addEventListener("change", (e) => {
            state.selectedFunctionIndex = parseInt(e.target.value, 10);
            renderCurrentCfg();
        });

        // CFG View Toggles
        elements.cfgViewPills.forEach(pill => {
            pill.addEventListener("click", () => {
                elements.cfgViewPills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                const view = pill.getAttribute("data-cfg-view");
                state.activeCfgView = view;

                elements.cfgViewSvg.classList.toggle("active", view === "svg");
                elements.cfgViewTable.classList.toggle("active", view === "table");
                elements.cfgViewDot.classList.toggle("active", view === "dot");
            });
        });

        // Copy DOT
        elements.btnCopyDot.addEventListener("click", () => {
            navigator.clipboard.writeText(elements.cfgDotCode.textContent).then(() => {
                elements.btnCopyDot.textContent = "Copied!";
                setTimeout(() => { elements.btnCopyDot.textContent = "Copy DOT"; }, 1500);
            });
        });

        // AST Expand / Collapse
        elements.btnExpandAst.addEventListener("click", () => {
            elements.astTreeContainer.querySelectorAll(".tree-node").forEach(n => {
                n.classList.remove("collapsed");
                const toggle = n.querySelector(".tree-toggle");
                if (toggle && toggle.textContent !== "•") toggle.textContent = "[-]";
            });
        });

        elements.btnCollapseAst.addEventListener("click", () => {
            elements.astTreeContainer.querySelectorAll(".tree-node").forEach(n => {
                n.classList.add("collapsed");
                const toggle = n.querySelector(".tree-toggle");
                if (toggle && toggle.textContent !== "•") toggle.textContent = "[+]";
            });
        });

        // Export Modal
        elements.btnExport.addEventListener("click", openExportModal);
        elements.btnCloseExport.addEventListener("click", () => elements.exportDialog.close());

        // Dismiss modal when clicking on the backdrop
        elements.exportDialog.addEventListener("click", (e) => {
            const rect = elements.exportDialog.getBoundingClientRect();
            const isInDialog = (
                rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
                rect.left <= e.clientX && e.clientX <= rect.left + rect.width
            );
            if (!isInDialog) {
                elements.exportDialog.close();
            }
        });

        elements.btnDownloadTxt.addEventListener("click", () => {
            const txt = elements.exportPreviewText.value;
            downloadFile("static_analysis_report.txt", txt, "text/plain");
        });

        elements.btnDownloadJson.addEventListener("click", () => {
            if (state.analysisResult) {
                const jsonStr = JSON.stringify(state.analysisResult, null, 2);
                downloadFile("static_analysis_data.json", jsonStr, "application/json");
            }
        });

        elements.btnCopyReport.addEventListener("click", () => {
            navigator.clipboard.writeText(elements.exportPreviewText.value).then(() => {
                elements.btnCopyReport.textContent = "Report Copied!";
                setTimeout(() => { elements.btnCopyReport.textContent = "Copy Text to Clipboard"; }, 1500);
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Run initialization
    document.addEventListener("DOMContentLoaded", init);
})();
