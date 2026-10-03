"""
End-to-End Pipeline for Natural Language to SQL Assistant.
Coordinates schema-aware prompting, LLM SQL generation, safety validation,
database execution, and natural-language insight synthesis.
"""

from typing import Dict, Any, Optional
from backend.schema_engine import schema_engine
from backend.validator import sql_validator, SQLValidationError
from backend.llm_client import llm_client
from backend.database import execute_query, get_dialect_name


class AISQLPipeline:
    def __init__(self):
        self.schema_engine = schema_engine
        self.validator = sql_validator
        self.llm = llm_client

    def process_query(self, natural_query: str, enforce_validation: bool = True) -> Dict[str, Any]:
        """
        Executes the full pipeline:
        1. Context Building: introspect schema and build prompt
        2. LLM Generation: generate SQL query from natural language
        3. Validation & Safety: AST check, destructive command blocking, LIMIT injection
        4. Execution: query PostgreSQL or SQLite database
        5. Synthesis: generate concise natural language answer
        """
        # Step 1: Introspect and build schema context
        schema_metadata = self.schema_engine.introspect_schema()
        schema_context = self.schema_engine.build_prompt_schema_context(natural_query)
        allowed_tables = set(schema_metadata["tables"].keys())
        relevant_tables = self.schema_engine.get_relevant_tables(natural_query)

        # Step 2: LLM SQL generation
        generated_sql = self.llm.generate_sql(schema_context, natural_query)

        # Step 3: SQL Safety Validation
        validation_result = None
        sql_to_run = generated_sql

        if enforce_validation:
            try:
                validation_result = self.validator.validate_and_prepare(
                    generated_sql,
                    allowed_tables=allowed_tables,
                    enforce_explain=True
                )
                sql_to_run = validation_result["sanitized_sql"]
            except SQLValidationError as e:
                return {
                    "status": "validation_error",
                    "error": str(e),
                    "error_details": e.details,
                    "natural_query": natural_query,
                    "generated_sql": generated_sql,
                    "sanitized_sql": None,
                    "relevant_tables": relevant_tables,
                    "dialect": get_dialect_name()
                }

        # Step 4: Execute query
        try:
            exec_result = execute_query(sql_to_run)
        except Exception as e:
            return {
                "status": "execution_error",
                "error": f"Database execution failed: {str(e)}",
                "natural_query": natural_query,
                "generated_sql": generated_sql,
                "sanitized_sql": sql_to_run,
                "validation": validation_result,
                "relevant_tables": relevant_tables,
                "dialect": get_dialect_name()
            }

        # Step 5: Synthesize concise natural-language response
        natural_answer = self.llm.synthesize_answer(
            natural_query=natural_query,
            sql_query=sql_to_run,
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            row_count=exec_result["row_count"]
        )

        return {
            "status": "success",
            "natural_query": natural_query,
            "generated_sql": generated_sql,
            "sanitized_sql": sql_to_run,
            "validation": validation_result,
            "execution": exec_result,
            "natural_answer": natural_answer,
            "relevant_tables": relevant_tables,
            "dialect": get_dialect_name()
        }


# Singleton pipeline instance
pipeline = AISQLPipeline()

