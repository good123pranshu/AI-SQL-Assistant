"""
Database management module.
Handles connection pooling, engine initialization, schema bootstrapping,
and safe execution for both PostgreSQL and SQLite databases.
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.config import settings, BASE_DIR
from backend.sample_data import Base, seed_sample_database

current_engine = None
current_session_factory = None
active_db_url = None


def get_engine(db_url: str = None):
    """Initializes or retrieves the active database engine."""
    global current_engine, current_session_factory, active_db_url

    url = db_url or active_db_url or settings.DATABASE_URL

    if current_engine is not None and active_db_url == url:
        return current_engine

    # If SQLite file path, ensure directory exists
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
        path_obj = Path(db_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
        engine = create_engine(url, connect_args=connect_args)
    else:
        # PostgreSQL or other SQL dialects
        engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)

    current_engine = engine
    active_db_url = url
    current_session_factory = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    return current_engine


def get_db_session():
    """Provides a transactional database session."""
    get_engine()
    session = current_session_factory()
    try:
        yield session
    finally:
        session.close()


def initialize_database(db_url: str = None):
    """Initializes tables and seeds sample data if needed."""
    engine = get_engine(db_url)
    Base.metadata.create_all(bind=engine)
    session = current_session_factory()
    try:
        seed_sample_database(session)
    finally:
        session.close()


def switch_database(new_url: str) -> Dict[str, Any]:
    """Switches connection to a new database URL (e.g. user-provided PostgreSQL)."""
    global current_engine, current_session_factory, active_db_url

    try:
        # Test connection first
        test_engine = create_engine(new_url)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Connection successful, update global engine
        if current_engine:
            current_engine.dispose()

        active_db_url = new_url
        current_engine = test_engine
        current_session_factory = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=test_engine))

        # Check tables
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        # If it's empty, create tables and seed demo data
        if len(tables) == 0:
            Base.metadata.create_all(bind=test_engine)
            session = current_session_factory()
            try:
                seed_sample_database(session)
            finally:
                session.close()
            tables = inspector.get_table_names()

        return {
            "status": "success",
            "url": new_url.split("@")[-1] if "@" in new_url else new_url,
            "dialect": test_engine.dialect.name,
            "tables": tables,
            "message": f"Successfully connected to {test_engine.dialect.name} database with {len(tables)} tables."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to database: {str(e)}"
        }


def execute_query(sql_query: str) -> Dict[str, Any]:
    """
    Executes a validated read-only SQL query against the active database.
    Returns column headers, row data, and execution duration in milliseconds.
    """
    engine = get_engine()
    start_time = time.perf_counter()

    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
        columns = list(result.keys()) if result.returns_rows else []
        rows = [list(row) for row in result.fetchall()] if result.returns_rows else []

    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": execution_time_ms
    }


def get_dialect_name() -> str:
    """Returns the dialect name (postgresql or sqlite) of current engine."""
    engine = get_engine()
    return engine.dialect.name

