/**
 * AI SQL Assistant Frontend Application
 */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let activeSchema = null;
    let sampleQueriesData = [];
    let currentResults = null;

    // DOM Elements
    const nlInput = document.getElementById("nl-input");
    const btnSubmit = document.getElementById("btn-submit");
    const btnClear = document.getElementById("btn-clear");
    const loadingState = document.getElementById("loading-state");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    const errorSqlBlock = document.getElementById("error-sql-block");
    const resultsContainer = document.getElementById("results-container");
    const nlAnswerText = document.getElementById("nl-answer-text");
    const sqlCodeView = document.getElementById("sql-code-view");
    const btnCopySql = document.getElementById("btn-copy-sql");
    const validationChecksList = document.getElementById("validation-checks-list");
    const resultsTableHead = document.getElementById("results-table-head");
    const resultsTableBody = document.getElementById("results-table-body");
    const resultsCountBadge = document.getElementById("results-count-badge");
    const executionTimeBadge = document.getElementById("execution-time-badge");
    const btnExportCsv = document.getElementById("btn-export-csv");
    const dbDialect = document.getElementById("db-dialect");
    const llmName = document.getElementById("llm-name");
    const schemaTree = document.getElementById("schema-tree");
    const schemaSearch = document.getElementById("schema-search");
    const schemaTableCount = document.getElementById("schema-table-count");
    const schemaRelCount = document.getElementById("schema-rel-count");
    const sampleTabs = document.getElementById("sample-tabs");
    const sampleChipsContainer = document.getElementById("sample-chips-container");
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-msg");

    // Modals
    const modalDbConnect = document.getElementById("modal-db-connect");
    const btnConnectDb = document.getElementById("btn-connect-db");
    const btnCloseDbModal = document.getElementById("btn-close-db-modal");
    const inputDbUrl = document.getElementById("input-db-url");
    const btnSaveDbUrl = document.getElementById("btn-save-db-url");
    const btnResetDemoDb = document.getElementById("btn-reset-demo-db");

    const modalSettings = document.getElementById("modal-settings");
    const btnOpenSettings = document.getElementById("btn-open-settings");
    const btnCloseSettingsModal = document.getElementById("btn-close-settings-modal");
    const selectLlmProvider = document.getElementById("select-llm-provider");
    const inputGeminiKey = document.getElementById("input-gemini-key");
    const inputOpenaiKey = document.getElementById("input-openai-key");
    const inputMaxRows = document.getElementById("input-max-rows");
    const btnSaveSettings = document.getElementById("btn-save-settings");

    // Initialize Lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // Show Toast
    function showToast(message, isError = false) {
        toastMsg.textContent = message;
        toast.className = `fixed bottom-6 right-6 z-50 transform translate-y-0 opacity-100 transition duration-300 px-4 py-3 rounded-xl border text-xs shadow-2xl flex items-center space-x-2 ${
            isError ? "bg-rose-950/90 border-rose-800 text-rose-200" : "bg-slate-800/90 border-slate-700 text-slate-100"
        }`;
        setTimeout(() => {
            toast.className = "fixed bottom-6 right-6 z-50 transform translate-y-20 opacity-0 transition duration-300 px-4 py-3 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white shadow-2xl flex items-center space-x-2 pointer-events-none";
        }, 3200);
    }

    // Fetch Health and Active Settings
    async function fetchHealth() {
        try {
            const res = await fetch("/api/health");
            const data = await res.json();
            dbDialect.textContent = data.dialect.toUpperCase() + (data.db_url && data.db_url.includes("ecommerce_demo") ? " (Demo)" : " DB");
            llmName.textContent = data.llm_provider ? data.llm_provider.toUpperCase() : "MOCK";
            selectLlmProvider.value = data.llm_provider || "mock";
        } catch (e) {
            console.error("Health fetch error:", e);
        }
    }

    // Fetch Schema and Render Tree
    async function fetchSchema() {
        try {
            const res = await fetch("/api/schema");
            activeSchema = await res.json();
            renderSchemaTree(activeSchema);
        } catch (e) {
            schemaTree.innerHTML = `<div class="p-3 text-rose-400">Failed to load schema</div>`;
        }
    }

    function renderSchemaTree(schema, filterText = "") {
        if (!schema || !schema.tables) return;

        const tableNames = Object.keys(schema.tables);
        schemaTableCount.textContent = `${tableNames.length} tables`;
        schemaRelCount.textContent = `${(schema.relationships || []).length} Links`;

        const filter = filterText.toLowerCase();
        let html = "";

        for (const tblName of tableNames) {
            const tbl = schema.tables[tblName];
            const matchesTable = tblName.toLowerCase().includes(filter);
            const matchingCols = tbl.columns.filter(c => c.name.toLowerCase().includes(filter));

            if (filter && !matchesTable && matchingCols.length === 0) {
                continue;
            }

            html += `
            <div class="border border-slate-800/80 rounded-xl bg-slate-900/60 overflow-hidden mb-2">
                <button class="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-slate-800/40 transition group" onclick="this.nextElementSibling.classList.toggle('hidden')">
                    <div class="flex items-center space-x-2">
                        <i data-lucide="table" class="w-3.5 h-3.5 text-indigo-400"></i>
                        <span class="font-medium text-slate-200 group-hover:text-indigo-300 transition">${tblName}</span>
                    </div>
                    <span class="text-[10px] text-slate-500 font-mono">${tbl.row_count} rows</span>
                </button>
                <div class="px-3 py-2 border-t border-slate-800/60 bg-black/20 space-y-1.5 ${filter ? '' : 'hidden'}">
            `;

            for (const col of tbl.columns) {
                const isPk = col.is_pk;
                html += `
                    <div class="flex items-center justify-between text-[11px] text-slate-400 hover:text-slate-200">
                        <div class="flex items-center space-x-1.5">
                            <span class="${isPk ? 'text-amber-400 font-semibold' : 'text-slate-400'}">${col.name}</span>
                            ${isPk ? '<span class="text-[9px] px-1 bg-amber-500/10 text-amber-400 rounded">PK</span>' : ''}
                        </div>
                        <span class="text-[10px] text-slate-500 font-mono">${col.type.split('(')[0]}</span>
                    </div>
                `;
            }

            html += `</div></div>`;
        }

        if (html === "") {
            schemaTree.innerHTML = `<div class="p-4 text-center text-slate-500">No matching tables found</div>`;
        } else {
            schemaTree.innerHTML = html;
        }

        if (window.lucide) lucide.createIcons();
    }

    schemaSearch.addEventListener("input", (e) => {
        renderSchemaTree(activeSchema, e.target.value);
    });

    // Fetch Sample Queries
    async function fetchSampleQueries() {
        try {
            const res = await fetch("/api/sample-queries");
            sampleQueriesData = await res.json();
            renderSampleTabs();
            renderSampleChips(0);
        } catch (e) {
            console.error("Failed to load sample queries", e);
        }
    }

    function renderSampleTabs() {
        sampleTabs.innerHTML = "";
        sampleQueriesData.forEach((cat, idx) => {
            const btn = document.createElement("button");
            btn.className = `px-2.5 py-1 rounded-md transition ${idx === 0 ? "bg-indigo-600/30 text-indigo-300 font-medium" : "text-slate-400 hover:text-slate-200"}`;
            btn.textContent = cat.category;
            btn.addEventListener("click", () => {
                Array.from(sampleTabs.children).forEach(c => c.className = "px-2.5 py-1 rounded-md text-slate-400 hover:text-slate-200 transition");
                btn.className = "px-2.5 py-1 rounded-md bg-indigo-600/30 text-indigo-300 font-medium transition";
                renderSampleChips(idx);
            });
            sampleTabs.appendChild(btn);
        });
    }

    function renderSampleChips(catIdx) {
        sampleChipsContainer.innerHTML = "";
        const cat = sampleQueriesData[catIdx];
        if (!cat) return;

        cat.queries.forEach(queryText => {
            const chip = document.createElement("button");
            const isDanger = queryText.toUpperCase().includes("DROP") || queryText.toUpperCase().includes("DELETE");
            chip.className = `text-left text-xs px-3 py-1.5 rounded-lg border transition ${
                isDanger
                    ? "bg-rose-950/30 border-rose-800/60 text-rose-300 hover:bg-rose-900/40"
                    : "bg-slate-900/80 border-slate-800 text-slate-300 hover:border-indigo-500/50 hover:bg-indigo-950/20"
            }`;
            chip.innerHTML = `${isDanger ? '<i data-lucide="shield-alert" class="w-3 h-3 inline mr-1 text-rose-400"></i>' : ''}${queryText}`;
            chip.addEventListener("click", () => {
                nlInput.value = queryText;
                submitQuery();
            });
            sampleChipsContainer.appendChild(chip);
        });

        if (window.lucide) lucide.createIcons();
    }

    // Submit Query
    async function submitQuery() {
        const text = nlInput.value.trim();
        if (!text) {
            showToast("Please enter a question or query.", true);
            return;
        }

        // Reset UI states
        errorCard.classList.add("hidden");
        resultsContainer.classList.add("hidden");
        loadingState.classList.remove("hidden");
        btnSubmit.disabled = true;

        try {
            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: text, enforce_validation: true })
            });

            const data = await res.json();
            loadingState.classList.add("hidden");
            btnSubmit.disabled = false;

            if (data.status === "validation_error") {
                renderValidationError(data);
            } else if (data.status === "execution_error") {
                renderExecutionError(data);
            } else if (data.status === "success") {
                renderSuccessResults(data);
            } else {
                throw new Error(data.detail || "Unexpected response");
            }
        } catch (e) {
            loadingState.classList.add("hidden");
            btnSubmit.disabled = false;
            errorMessage.textContent = e.message || "Failed to process query.";
            errorSqlBlock.classList.add("hidden");
            errorCard.classList.remove("hidden");
        }
    }

    // Render Validation Error (e.g. DROP, DELETE, stacked queries, syntax errors)
    function renderValidationError(data) {
        document.getElementById("error-title").textContent = "Safety Guardrail Blocked Query";
        document.getElementById("error-type").textContent = "Validation Shield Triggered";
        errorMessage.textContent = data.error;

        if (data.generated_sql) {
            errorSqlBlock.textContent = data.generated_sql;
            errorSqlBlock.classList.remove("hidden");
        } else {
            errorSqlBlock.classList.add("hidden");
        }

        errorCard.classList.remove("hidden");
        showToast("Query blocked by SQL safety guardrail!", true);
    }

    // Render Execution Error
    function renderExecutionError(data) {
        document.getElementById("error-title").textContent = "Database Execution Error";
        document.getElementById("error-type").textContent = "DB Error";
        errorMessage.textContent = data.error;

        if (data.sanitized_sql) {
            errorSqlBlock.textContent = data.sanitized_sql;
            errorSqlBlock.classList.remove("hidden");
        }

        errorCard.classList.remove("hidden");
    }

    // Render Success Results
    function renderSuccessResults(data) {
        currentResults = data.execution;

        // 1. Natural Language Answer
        nlAnswerText.textContent = data.natural_answer;

        // 2. SQL Display
        sqlCodeView.textContent = data.sanitized_sql || data.generated_sql;

        // 3. Validation Badges
        validationChecksList.innerHTML = "";
        const checks = (data.validation && data.validation.checks_passed) || [
            "AST confirmed read-only SELECT",
            "No destructive operations",
            "LIMIT clause enforced"
        ];
        checks.forEach(chk => {
            const badge = document.createElement("span");
            badge.className = "inline-flex items-center space-x-1 text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700/80 text-slate-300";
            badge.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span>${chk}</span>`;
            validationChecksList.appendChild(badge);
        });

        // 4. Execution Metrics
        const exec = data.execution;
        resultsCountBadge.textContent = `${exec.row_count} row${exec.row_count === 1 ? '' : 's'}`;
        executionTimeBadge.textContent = `${exec.execution_time_ms} ms`;

        // 5. Results Table
        renderTable(exec.columns, exec.rows);

        resultsContainer.classList.remove("hidden");
        resultsContainer.classList.add("fade-in");

        if (window.lucide) lucide.createIcons();
    }

    function renderTable(columns, rows) {
        // Render headers
        resultsTableHead.innerHTML = `<tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr>`;

        // Render rows
        if (!rows || rows.length === 0) {
            resultsTableBody.innerHTML = `
                <tr>
                    <td colspan="${columns.length || 1}" class="text-center py-8 text-slate-500 italic">
                        No rows returned for this query.
                    </td>
                </tr>
            `;
            return;
        }

        resultsTableBody.innerHTML = rows.map(row => {
            return `<tr>${row.map(val => {
                let formatted = val;
                if (val === null || val === undefined) {
                    formatted = `<span class="text-slate-500 italic">null</span>`;
                } else if (typeof val === "number") {
                    formatted = `<span class="font-mono text-indigo-300">${val}</span>`;
                }
                return `<td>${formatted}</td>`;
            }).join('')}</tr>`;
        }).join('');
    }

    // Copy SQL button
    btnCopySql.addEventListener("click", () => {
        const sql = sqlCodeView.textContent;
        navigator.clipboard.writeText(sql);
        showToast("SQL query copied to clipboard!");
    });

    // Clear input
    btnClear.addEventListener("click", () => {
        nlInput.value = "";
        nlInput.focus();
    });

    // Submit on click
    btnSubmit.addEventListener("click", submitQuery);

    // Ctrl + Enter shortcut
    nlInput.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            submitQuery();
        }
    });

    // CSV Export
    btnExportCsv.addEventListener("click", () => {
        if (!currentResults || !currentResults.columns) return;
        const cols = currentResults.columns;
        const rows = currentResults.rows;

        let csv = cols.join(",") + "\n";
        rows.forEach(r => {
            const line = r.map(val => {
                if (val === null || val === undefined) return "";
                const str = String(val).replace(/"/g, '""');
                return `"${str}"`;
            }).join(",");
            csv += line + "\n";
        });

        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `sql_query_result_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("Exported results to CSV!");
    });

    // DB Modal Handlers
    btnConnectDb.addEventListener("click", () => modalDbConnect.classList.remove("hidden"));
    btnCloseDbModal.addEventListener("click", () => modalDbConnect.classList.add("hidden"));

    btnSaveDbUrl.addEventListener("click", async () => {
        const url = inputDbUrl.value.trim();
        if (!url) {
            showToast("Please enter a database connection URL", true);
            return;
        }

        try {
            const res = await fetch("/api/database/connect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ database_url: url })
            });
            const data = await res.json();
            if (data.status === "error") throw new Error(data.message);

            showToast("Connected to database successfully!");
            modalDbConnect.classList.add("hidden");
            await fetchHealth();
            await fetchSchema();
        } catch (e) {
            showToast(e.message || "Failed to connect to database", true);
        }
    });

    btnResetDemoDb.addEventListener("click", async () => {
        try {
            await fetch("/api/database/reset-demo", { method: "POST" });
            showToast("Reset to default SQLite Demo database.");
            modalDbConnect.classList.add("hidden");
            await fetchHealth();
            await fetchSchema();
        } catch (e) {
            showToast("Failed to reset database", true);
        }
    });

    // Settings Modal Handlers
    btnOpenSettings.addEventListener("click", () => modalSettings.classList.remove("hidden"));
    btnCloseSettingsModal.addEventListener("click", () => modalSettings.classList.add("hidden"));

    btnSaveSettings.addEventListener("click", async () => {
        const provider = selectLlmProvider.value;
        const geminiKey = inputGeminiKey.value.trim();
        const openaiKey = inputOpenaiKey.value.trim();
        const maxRows = parseInt(inputMaxRows.value, 10);

        try {
            await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    llm_provider: provider,
                    gemini_api_key: geminiKey || undefined,
                    openai_api_key: openaiKey || undefined,
                    max_query_rows: isNaN(maxRows) ? 100 : maxRows
                })
            });

            showToast("Settings updated successfully!");
            modalSettings.classList.add("hidden");
            await fetchHealth();
        } catch (e) {
            showToast("Failed to update settings", true);
        }
    });

    // Sidebar schema toggle on mobile
    const btnSchemaToggle = document.getElementById("btn-schema-toggle");
    const schemaSidebar = document.getElementById("schema-sidebar");
    btnSchemaToggle.addEventListener("click", () => {
        schemaSidebar.classList.toggle("hidden");
    });

    // Initial load
    fetchHealth();
    fetchSchema();
    fetchSampleQueries();
});

