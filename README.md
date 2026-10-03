# 🤖 AI SQL Assistant: Natural Language to SQL

An enterprise-ready AI assistant that converts natural-language business questions into validated, optimized SQL queries and executes them safely against **PostgreSQL** or **SQLite**, returning structured data and executive natural-language insights.

Built with **Python**, **FastAPI**, **LLMs** (OpenAI, Gemini, Ollama, & Mock engine), **SQLAlchemy**, and **Multi-Layer AST Safety Guardrails**.

---

## 🌟 Key Highlights

- **Natural Language to SQL**: Converts plain English analytics inquiries into dialect-accurate SQL.
- **Schema-Aware Prompting Pipeline**: Dynamically introspects live tables, column types, primary/foreign keys, and categorical sample values to generate zero-hallucination JOIN paths and filters.
- **Multi-Layer SQL Safety Guardrails**:
  1. **Multi-Statement Blocker**: Strictly prevents stacked SQL injection (e.g. `SELECT 1; DROP TABLE users;`).
  2. **Destructive Command Blocker**: Enforces read-only behavior; blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `PRAGMA`.
  3. **AST Syntax & Type Verification**: Validates query AST using `sqlglot` to verify the root expression is an `exp.Select` or CTE.
  4. **Table & Column Whitelist**: Validates all referenced tables against active database schema.
  5. **Automated LIMIT Injection**: Automatically injects or caps queries with `LIMIT 100` to prevent memory exhaustion and runaway scans.
  6. **EXPLAIN Pre-flight Check**: Verifies database query planner compatibility without executing side-effects.
- **Dual Engine Support**: Instant zero-configuration demo with **SQLite** (pre-seeded with e-commerce data) + seamless live **PostgreSQL** connection.
- **Executive Insight Generation**: Synthesizes query results into crisp 1–3 sentence business summaries with metrics.
- **Modern Responsive Web UI**: Tailwind CSS dark-mode dashboard with live schema tree explorer, SQL syntax viewer, safety checklist, and CSV export.

---

## 🏗️ Architecture Pipeline

```mermaid
flowchart TD
    User([User Natural Language Query]) --> API[FastAPI /api/query]
    
    subgraph Schema_Engine [Schema-Aware Prompting Engine]
        DB[(PostgreSQL / SQLite)] -->|Introspect| Meta[Tables, Types, Constraints & FKs]
        Meta -->|Extract Low-Cardinality| Samples[Categorical Samples]
        Samples --> Context[Dialect-Specific Prompt Context]
    end

    API --> Schema_Engine
    Context --> LLM[LLM: OpenAI / Gemini / Ollama / Mock]
    User --> LLM
    LLM --> RawSQL[Generated Raw SQL]

    subgraph Safety_Guardrails [Multi-Layer SQL Validator]
        RawSQL --> Clean[Sanitizer & De-fence]
        Clean --> MultiCheck{Multi-statement?}
        MultiCheck -->|Yes| Block1[Reject Stacked Injection]
        MultiCheck -->|No| DestructCheck{Destructive Keyword?}
        DestructCheck -->|Yes| Block2[Reject DDL/DML Mutation]
        DestructCheck -->|No| AST[AST Parser: sqlglot]
        AST --> Whitelist[Table Whitelist Check]
        Whitelist --> LimitInj[Inject / Cap Safe LIMIT]
        LimitInj --> Explain[EXPLAIN Plan Verification]
    end

    Explain --> SafeSQL[Validated Safe SQL]
    SafeSQL --> Exec[Execute Query on Database]
    Exec --> Results[(Tabular Data Result)]

    subgraph Synthesizer [Natural Language Synthesizer]
        Results --> LLMSynth[Insight Synthesis]
        User --> LLMSynth
        LLMSynth --> Answer[Executive Business Insight]
    end

    Answer --> Output([Dashboard UI / REST Client])
    Results --> Output
    SafeSQL --> Output
```

---

## 📂 Project Structure

```
AI SQL Assistant/
├── backend/
│   ├── config.py              # Environment variables & runtime settings
│   ├── database.py            # SQLAlchemy pooling, session management & execution
│   ├── sample_data.py         # E-commerce schema & dataset seeder (customers, orders, products, reviews)
│   ├── schema_engine.py       # Live DB introspection & schema-aware context builder
│   ├── validator.py           # Multi-layered AST safety validator & LIMIT injector
│   ├── llm_client.py          # Unified LLM provider (OpenAI, Gemini, Ollama, Mock generator)
│   ├── pipeline.py            # End-to-end NL-to-SQL orchestration
│   └── main.py                # FastAPI endpoints, CORS, static frontend serving
├── frontend/
│   ├── index.html             # Responsive dark-theme dashboard UI
│   ├── app.js                 # Frontend application state, schema tree, query runner, CSV export
│   └── style.css              # Custom styling, animations, table highlights
├── tests/
│   ├── test_validator.py      # Unit tests: DDL/DML blocking, injection defense, LIMIT injection
│   ├── test_schema_engine.py  # Tests: DB introspection, FK relation links, prompt formatting
│   ├── test_pipeline.py       # Integration tests: End-to-end question processing
│   └── test_api.py            # FastAPI REST endpoint integration tests
├── docker-compose.yml         # Pre-configured PostgreSQL 16 + pgAdmin container
├── .env.example               # Template environment configuration
├── requirements.txt           # Dependencies specification
├── run.py                     # One-click startup script
└── README.md                  # Project documentation & resume guide
```

---

## ⚡ Quickstart

### 1. Run with Zero Setup (SQLite Demo)
The assistant includes an intelligent offline mock/rule engine and a realistic e-commerce database, allowing you to run and evaluate everything immediately:

```bash
# Clone the repository
git clone https://github.com/your-username/ai-sql-assistant.git
cd "ai-sql-assistant"

# Install dependencies
pip install -r requirements.txt

# Launch the server
python run.py
```

Open your browser at: **`http://127.0.0.1:8000`**

---

### 2. Run with PostgreSQL & Docker (Optional)
To use a real PostgreSQL 16 database:

```bash
# 1. Start PostgreSQL with Docker Compose
docker compose up -d

# 2. Set database connection in .env or via Web Dashboard
DATABASE_URL=postgresql://postgres:password123@localhost:5432/ecommerce

# 3. Start the application
python run.py
```

---

### 3. Configure External LLMs (Gemini / OpenAI / Ollama)
You can configure providers in `.env` or directly through the **Settings modal in the Web UI**:

```bash
# Google Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Ollama (Local LLM)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## 🛡️ SQL Safety & Validation Deep Dive

Unlike naive text-to-SQL wrappers that execute raw LLM outputs, this system implements **defense-in-depth**:

| Layer | Security Mechanism | Threat Prevented |
| :--- | :--- | :--- |
| **Layer 1: Sanitization** | Code-fence stripping and semicolon normalization | Formatting syntax errors and query confusion |
| **Layer 2: Multi-Statement Detection** | Splits by `;` and rejects queries with $> 1$ statement | Stacked SQL Injection (e.g. `; DROP TABLE orders;`) |
| **Layer 3: Destructive Command Blocker** | Regex boundary scan for `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `PRAGMA` | Unintended or malicious database mutations |
| **Layer 4: AST Syntax Verification** | Parses query into AST with `sqlglot` and verifies `isinstance(parsed, exp.Select)` | Malformed queries, unauthorized statement types |
| **Layer 5: Schema Table Whitelist** | Verifies every AST `exp.Table` exists in inspected database schema | Hallucinated or unauthorized table access |
| **Layer 6: LIMIT Injection & Capping** | Automatically injects `LIMIT 100` if missing; caps if higher | Out-Of-Memory (OOM) crashes and runaway table scans |
| **Layer 7: Pre-Flight EXPLAIN Check** | Executes `EXPLAIN <sql>` against target engine before real run | Execution plan verification without data retrieval |

---

## 📊 Sample Queries to Try

### Customer Analytics
- *"Show the top 5 customers by total spending and order count"*
- *"Find all customers who haven't placed an order yet"*
- *"What is the breakdown of customers by country?"*

### Sales & Inventory Performance
- *"Which product categories generated the most revenue?"*
- *"Find all products with low stock (less than 50 units) ordered by stock"*
- *"Show the top 5 best selling products by total units sold"*

### Safety Guardrail Tests (Expected: BLOCKED)
- `DROP TABLE customers;` $\rightarrow$ **Blocked by Layer 3 (Destructive command)**
- `DELETE FROM orders WHERE total_amount > 100;` $\rightarrow$ **Blocked by Layer 3 (DML mutation)**
- `SELECT * FROM customers; DROP TABLE orders;` $\rightarrow$ **Blocked by Layer 2 (Stacked queries)**

---


