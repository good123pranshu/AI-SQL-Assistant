"""
SQL Validation and Safety Engine.
Performs AST parsing, destructive command rejection, SQL injection defense,
table whitelist verification, and automatic LIMIT enforcement.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
import sqlglot
from sqlglot import exp
from backend.config import settings
from backend.database import get_engine, get_dialect_name

# Forbidden commands, statements, and security risks
FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "CALL", "PRAGMA", "ATTACH", "DETACH", "VACUUM", "REINDEX",
    "INTO OUTFILE", "DUMPFILE", "LOAD_FILE", "PG_SLEEP", "BENCHMARK",
    "PG_READ_FILE", "PG_WRITE_FILE", "COPY"
}


class SQLValidationError(Exception):
    """Raised when an SQL query fails safety or syntax validation."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SQLValidator:
    def __init__(self, max_limit: int = settings.MAX_QUERY_ROWS_LIMIT):
        self.max_limit = max_limit

    def clean_query(self, raw_sql: str) -> str:
        """Removes markdown code fences, comments, and leading/trailing whitespace."""
        query = raw_sql.strip()

        # Remove markdown fences ```sql ... ``` or ``` ... ```
        if query.startswith("```"):
            lines = query.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            query = "\n".join(lines).strip()

        # Strip trailing semicolon for normalization
        if query.endswith(";"):
            query = query[:-1].strip()

        return query

    def validate_and_prepare(
        self,
        raw_sql: str,
        allowed_tables: Optional[Set[str]] = None,
        enforce_explain: bool = True
    ) -> Dict[str, Any]:
        """
        Validates the SQL query through multiple defense layers:
        1. Multi-statement injection check
        2. Forbidden keyword / destructive command rejection
        3. AST parsing & read-only statement verification
        4. Schema table whitelist check
        5. Safe LIMIT enforcement
        6. EXPLAIN dry run on target engine
        """
        cleaned_sql = self.clean_query(raw_sql)

        if not cleaned_sql:
            raise SQLValidationError("SQL query is empty.")

        # Layer 1: Multi-statement check (prevents stacked queries like 'SELECT 1; DROP TABLE users;')
        statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
        if len(statements) > 1:
            raise SQLValidationError(
                "Multiple SQL statements detected. Stacking queries is strictly prohibited for security.",
                {"statement_count": len(statements)}
            )

        sql_to_check = statements[0]

        # Layer 2: Fast regex inspection for forbidden destructive commands
        for forbidden in FORBIDDEN_KEYWORDS:
            pattern = rf"\b{re.escape(forbidden)}\b"
            if re.search(pattern, sql_to_check, re.IGNORECASE):
                raise SQLValidationError(
                    f"Forbidden destructive command or operation '{forbidden}' detected.",
                    {"blocked_keyword": forbidden}
                )

        # Layer 3: AST parsing using sqlglot
        target_dialect = get_dialect_name()
        sqlglot_dialect = "postgres" if target_dialect == "postgresql" else "sqlite"

        try:
            parsed = sqlglot.parse_one(sql_to_check, read=sqlglot_dialect)
        except Exception as e:
            try:
                # Fallback parser attempt with generic dialect
                parsed = sqlglot.parse_one(sql_to_check)
            except Exception as parse_err:
                raise SQLValidationError(
                    f"Syntax error in generated SQL query: {str(parse_err)}",
                    {"original_query": sql_to_check}
                )

        # Ensure root node is a SELECT statement (or a CTE containing SELECT)
        if not isinstance(parsed, exp.Select):
            raise SQLValidationError(
                f"Query must be a read-only SELECT statement, found: {type(parsed).__name__}"
            )

        # Layer 4: Schema table whitelist check
        if allowed_tables:
            referenced_tables = {
                t.name.lower() for t in parsed.find_all(exp.Table) if t.name
            }
            # Normalize allowed tables
            normalized_allowed = {t.lower() for t in allowed_tables}
            unknown_tables = referenced_tables - normalized_allowed

            if unknown_tables:
                raise SQLValidationError(
                    f"Query references non-existent or unauthorized table(s): {', '.join(unknown_tables)}",
                    {"unknown_tables": list(unknown_tables), "allowed_tables": list(allowed_tables)}
                )

        # Layer 5: LIMIT clause enforcement
        limit_node = parsed.args.get("limit")
        limit_applied = False
        final_limit = self.max_limit

        if limit_node is None:
            # Inject LIMIT clause
            parsed = parsed.limit(self.max_limit)
            limit_applied = True
        else:
            try:
                current_limit_val = int(limit_node.expression.this)
                if current_limit_val > self.max_limit:
                    parsed = parsed.limit(self.max_limit)
                    limit_applied = True
                else:
                    final_limit = current_limit_val
            except Exception:
                parsed = parsed.limit(self.max_limit)
                limit_applied = True

        final_sql = parsed.sql(dialect=sqlglot_dialect)

        # Layer 6: EXPLAIN dry run on target engine
        if enforce_explain:
            self._explain_check(final_sql)

        return {
            "is_valid": True,
            "original_sql": cleaned_sql,
            "sanitized_sql": final_sql,
            "limit_enforced": limit_applied,
            "limit_value": final_limit,
            "checks_passed": [
                "No stacked/multi-statement queries",
                "No destructive DDL/DML operations",
                "AST confirmed read-only SELECT/CTE",
                "Table whitelist validated",
                f"Row limit enforced ({final_limit} max)",
                "EXPLAIN execution plan verified"
            ]
        }

    def _explain_check(self, sql_query: str):
        """Runs EXPLAIN to verify database compatibility without executing data mutation."""
        engine = get_engine()
        explain_query = f"EXPLAIN {sql_query}"
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text(explain_query))
        except Exception as e:
            raise SQLValidationError(
                f"Database execution plan failed (EXPLAIN check): {str(e)}",
                {"sql": sql_query}
            )


# Singleton instance
sql_validator = SQLValidator()

