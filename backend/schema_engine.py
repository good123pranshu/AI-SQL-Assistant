"""
Schema-aware Prompting Engine.
Extracts live database schema (tables, columns, types, primary/foreign keys, sample values),
performs intelligent relevance ranking, and formats rich context for the LLM prompt.
"""

from typing import Dict, Any, List, Optional, Set
from sqlalchemy import inspect, text
from backend.database import get_engine, get_dialect_name


class SchemaEngine:
    def __init__(self):
        self._schema_cache: Optional[Dict[str, Any]] = None

    def introspect_schema(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Extracts structural metadata from the database:
        - Tables and their descriptions
        - Columns (names, types, nullability, primary keys)
        - Foreign Key constraints and relationship links
        - Low-cardinality sample values for categorical columns
        - Approximate row counts
        """
        if self._schema_cache and not force_refresh:
            return self._schema_cache

        engine = get_engine()
        inspector = inspect(engine)
        dialect = get_dialect_name()

        tables_info = {}
        foreign_keys_summary = []

        table_names = inspector.get_table_names()

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
            fks = inspector.get_foreign_keys(table_name)

            col_details = []
            for col in columns:
                cname = col["name"]
                ctype = str(col["type"])
                is_pk = cname in pk_cols
                is_nullable = col.get("nullable", True)

                col_info = {
                    "name": cname,
                    "type": ctype,
                    "is_pk": is_pk,
                    "nullable": is_nullable,
                    "sample_values": []
                }

                # Extract sample values for text/category columns to help LLM write accurate filters
                if "VARCHAR" in ctype.upper() or "TEXT" in ctype.upper() or "STRING" in ctype.upper():
                    try:
                        with engine.connect() as conn:
                            sample_query = text(
                                f"SELECT DISTINCT {cname} FROM {table_name} WHERE {cname} IS NOT NULL LIMIT 5"
                            )
                            samples = [str(r[0]) for r in conn.execute(sample_query).fetchall() if r[0] is not None]
                            if samples and len(samples) <= 5:
                                col_info["sample_values"] = samples
                    except Exception:
                        pass

                col_details.append(col_info)

            # Record foreign keys
            fk_details = []
            for fk in fks:
                referred_table = fk.get("referred_table")
                for c_col, r_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                    relation_str = f"{table_name}.{c_col} -> {referred_table}.{r_col}"
                    fk_details.append(relation_str)
                    foreign_keys_summary.append({
                        "from_table": table_name,
                        "from_column": c_col,
                        "to_table": referred_table,
                        "to_column": r_col,
                        "relation": relation_str
                    })

            # Get row count
            row_count = 0
            try:
                with engine.connect() as conn:
                    cnt_res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = cnt_res.scalar() or 0
            except Exception:
                pass

            tables_info[table_name] = {
                "name": table_name,
                "columns": col_details,
                "foreign_keys": fk_details,
                "row_count": row_count
            }

        self._schema_cache = {
            "dialect": dialect,
            "tables": tables_info,
            "relationships": foreign_keys_summary
        }
        return self._schema_cache

    def get_relevant_tables(self, natural_query: str) -> List[str]:
        """
        Identifies tables relevant to the user query based on keyword overlap
        and joins in related foreign key tables.
        """
        schema = self.introspect_schema()
        all_tables = list(schema["tables"].keys())

        # If schema is compact (<= 8 tables), return all tables to give full context
        if len(all_tables) <= 8:
            return all_tables

        query_tokens = set(natural_query.lower().split())
        scored_tables = []

        for tbl_name, tbl_meta in schema["tables"].items():
            score = 0
            # Table name match
            if tbl_name.lower() in natural_query.lower():
                score += 5

            # Column name match
            for col in tbl_meta["columns"]:
                cname = col["name"].lower()
                if cname in query_tokens or cname in natural_query.lower():
                    score += 2
                for s in col.get("sample_values", []):
                    if s.lower() in natural_query.lower():
                        score += 3

            if score > 0:
                scored_tables.append((tbl_name, score))

        # Sort by relevance
        scored_tables.sort(key=lambda x: x[1], reverse=True)
        selected = {tbl for tbl, _ in scored_tables[:4]}

        # If none matched directly, fallback to all tables
        if not selected:
            return all_tables

        # Expand with directly connected foreign key tables
        connected = set(selected)
        for rel in schema["relationships"]:
            if rel["from_table"] in selected:
                connected.add(rel["to_table"])
            if rel["to_table"] in selected:
                connected.add(rel["from_table"])

        return list(connected)

    def build_prompt_schema_context(self, natural_query: str) -> str:
        """
        Generates schema prompt context including:
        - Target database dialect and specific syntax rules
        - Relevant tables with columns, types, primary keys, and sample categorical values
        - Foreign key relationships to facilitate correct JOINs
        """
        schema = self.introspect_schema()
        dialect = schema["dialect"]
        relevant_tables = self.get_relevant_tables(natural_query)

        lines = [
            f"=== TARGET DATABASE DIALECT: {dialect.upper()} ===",
            "SYNTAX INSTRUCTIONS:",
            f"- Generate syntactically valid {dialect.upper()} SQL queries only.",
            "- Never produce destructive operations (no DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE).",
            "- Only generate read-only SELECT or WITH...SELECT queries.",
            "- Wrap column or table names if necessary, and use standard SQL JOIN syntax.",
        ]

        if dialect == "postgresql":
            lines.extend([
                "- For case-insensitive text matching, use ILIKE instead of LIKE.",
                "- For date/time extraction, use EXTRACT(YEAR/MONTH/DAY FROM column) or DATE_TRUNC('month', column).",
                "- Use double quotes for identifiers only if case-sensitive, otherwise lowercase is preferred."
            ])
        else:
            lines.extend([
                "- For case-insensitive text matching, use LIKE or LOWER(column) = LOWER(value).",
                "- For date/time extraction, use strftime('%Y', column), strftime('%m', column), etc."
            ])

        lines.append("\n=== DATABASE SCHEMA & CONSTRAINTS ===")
        for tbl_name in relevant_tables:
            tbl_info = schema["tables"].get(tbl_name)
            if not tbl_info:
                continue

            lines.append(f"\nTable: {tbl_name} (Approx. {tbl_info['row_count']} rows)")
            col_strs = []
            for col in tbl_info["columns"]:
                parts = [f"{col['name']} ({col['type']})"]
                if col["is_pk"]:
                    parts.append("PRIMARY KEY")
                if col.get("sample_values"):
                    samples_repr = ", ".join(f"'{s}'" for s in col["sample_values"][:4])
                    parts.append(f"examples: [{samples_repr}]")
                col_strs.append("  - " + " ".join(parts))
            lines.extend(col_strs)

        # Include relationships between relevant tables
        relevant_set = set(relevant_tables)
        rel_lines = []
        for rel in schema["relationships"]:
            if rel["from_table"] in relevant_set and rel["to_table"] in relevant_set:
                rel_lines.append(f"  - {rel['relation']}")

        if rel_lines:
            lines.append("\n=== FOREIGN KEY RELATIONSHIPS (JOIN PATHS) ===")
            lines.extend(rel_lines)

        return "\n".join(lines)


# Singleton instance
schema_engine = SchemaEngine()

