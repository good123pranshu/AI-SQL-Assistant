"""
FastAPI application entry point for AI SQL Assistant.
Provides RESTful APIs for natural-language query processing, SQL validation,
schema introspection, database management, and serves the frontend dashboard.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.database import (
    initialize_database,
    switch_database,
    execute_query,
    get_dialect_name,
    active_db_url
)
from backend.schema_engine import schema_engine
from backend.validator import sql_validator, SQLValidationError
from backend.pipeline import pipeline
from backend.llm_client import llm_client

from contextlib import asynccontextmanager

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    schema_engine.introspect_schema(force_refresh=True)
    yield

# Initialize application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Natural Language to SQL Assistant with Schema-Aware Prompting and SQL Safety Guardrails",
    lifespan=lifespan
)

# Enable CORS for local development and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request and Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question to convert and execute", min_length=2)
    enforce_validation: bool = Field(True, description="Whether to run multi-layer safety validation")


class ValidateRequest(BaseModel):
    sql: str = Field(..., description="Raw SQL query string to validate")


class ExecuteRequest(BaseModel):
    sql: str = Field(..., description="Validated SQL query to execute")


class DBConnectRequest(BaseModel):
    database_url: str = Field(..., description="PostgreSQL or SQLite connection URL")


class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_model: Optional[str] = None
    max_query_rows: Optional[int] = None


# API Routes
@app.get("/api/health")
def health_check():
    """Health status and active environment configuration."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "dialect": get_dialect_name(),
        "llm_provider": llm_client.provider,
        "db_url": active_db_url.split("@")[-1] if active_db_url and "@" in active_db_url else active_db_url
    }


@app.post("/api/query")
def process_natural_query(req: QueryRequest):
    """
    End-to-end endpoint:
    Natural language question -> Schema extraction -> LLM SQL generation ->
    Safety validation & LIMIT injection -> Query execution -> Concise natural language answer.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    result = pipeline.process_query(
        natural_query=req.query.strip(),
        enforce_validation=req.enforce_validation
    )
    return result


@app.post("/api/validate")
def validate_sql(req: ValidateRequest):
    """
    Validates an SQL query against syntax errors, destructive keywords,
    injection attacks, and unauthorized tables.
    """
    schema = schema_engine.introspect_schema()
    allowed_tables = set(schema["tables"].keys())

    try:
        validation_info = sql_validator.validate_and_prepare(
            raw_sql=req.sql,
            allowed_tables=allowed_tables,
            enforce_explain=True
        )
        return {"status": "valid", "details": validation_info}
    except SQLValidationError as e:
        return {
            "status": "invalid",
            "error": str(e),
            "details": e.details
        }


@app.post("/api/execute")
def execute_raw_sql(req: ExecuteRequest):
    """
    Safely executes an SQL query after passing validation checks.
    """
    schema = schema_engine.introspect_schema()
    allowed_tables = set(schema["tables"].keys())

    try:
        validation = sql_validator.validate_and_prepare(
            raw_sql=req.sql,
            allowed_tables=allowed_tables,
            enforce_explain=True
        )
        exec_result = execute_query(validation["sanitized_sql"])
        return {
            "status": "success",
            "executed_sql": validation["sanitized_sql"],
            "execution": exec_result
        }
    except SQLValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@app.get("/api/schema")
def get_schema():
    """Returns database tables, column definitions, data types, and foreign key relationships."""
    return schema_engine.introspect_schema()


@app.post("/api/database/connect")
def connect_database(req: DBConnectRequest):
    """Switches the database connection to a specified PostgreSQL or SQLite URL."""
    res = switch_database(req.database_url)
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    schema_engine.introspect_schema(force_refresh=True)
    return res


@app.post("/api/database/reset-demo")
def reset_demo_database():
    """Resets to the default e-commerce sample database."""
    default_url = f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'ecommerce_demo.db'}"
    res = switch_database(default_url)
    schema_engine.introspect_schema(force_refresh=True)
    return {"status": "success", "message": "Reset to sample e-commerce database."}


@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    """Updates runtime LLM and query configurations."""
    if req.llm_provider:
        settings.LLM_PROVIDER = req.llm_provider
        llm_client.provider = req.llm_provider.lower()
    if req.openai_api_key:
        settings.OPENAI_API_KEY = req.openai_api_key
    if req.gemini_api_key:
        settings.GEMINI_API_KEY = req.gemini_api_key
    if req.ollama_model:
        settings.OLLAMA_MODEL = req.ollama_model
    if req.max_query_rows:
        settings.MAX_QUERY_ROWS_LIMIT = req.max_query_rows
        sql_validator.max_limit = req.max_query_rows

    return {
        "status": "success",
        "settings": {
            "llm_provider": llm_client.provider,
            "has_openai_key": bool(settings.OPENAI_API_KEY),
            "has_gemini_key": bool(settings.GEMINI_API_KEY),
            "ollama_model": settings.OLLAMA_MODEL,
            "max_query_rows": sql_validator.max_limit
        }
    }


@app.get("/api/sample-queries")
def get_sample_queries():
    """Returns curated natural-language sample questions across different business categories."""
    return [
        {
            "category": "Customer Analytics",
            "queries": [
                "Show the top 5 customers by total spending and order count",
                "Find all customers who haven't placed an order yet",
                "What is the breakdown of customers by country?"
            ]
        },
        {
            "category": "Sales & Revenue",
            "queries": [
                "Which product categories generated the most revenue?",
                "What is the total revenue and count of orders grouped by status?",
                "Show the latest 10 orders with customer names and order values"
            ]
        },
        {
            "category": "Product & Inventory",
            "queries": [
                "Find all products with low stock (less than 50 units) ordered by stock",
                "Show the top 5 best selling products by total units sold",
                "Which product categories have the highest average rating?"
            ]
        },
        {
            "category": "Safety & Guardrail Demos",
            "queries": [
                "DROP TABLE customers;",
                "DELETE FROM orders WHERE total_amount > 100;",
                "SELECT * FROM customers; DROP TABLE orders;"
            ]
        }
    ]


# Mount frontend static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(frontend_dir / "index.html")
