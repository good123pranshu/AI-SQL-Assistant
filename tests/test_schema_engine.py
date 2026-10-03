"""
Unit tests for the Schema-Aware Prompting Engine.
Tests database introspection, relationship extraction, and prompt context building.
"""

import pytest
from backend.database import initialize_database
from backend.schema_engine import SchemaEngine


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database()


@pytest.fixture
def engine():
    return SchemaEngine()


def test_schema_introspection(engine):
    schema = engine.introspect_schema(force_refresh=True)
    assert "tables" in schema
    assert "relationships" in schema
    assert "customers" in schema["tables"]
    assert "orders" in schema["tables"]
    assert "products" in schema["tables"]

    # Verify columns and PK detection
    cust_cols = {c["name"]: c for c in schema["tables"]["customers"]["columns"]}
    assert "id" in cust_cols
    assert cust_cols["id"]["is_pk"] is True
    assert "email" in cust_cols


def test_relationships_extracted(engine):
    schema = engine.introspect_schema()
    relationships = schema["relationships"]
    assert len(relationships) >= 3

    # Check that orders.customer_id -> customers.id is detected
    found_order_customer_rel = any(
        r["from_table"] == "orders" and r["to_table"] == "customers"
        for r in relationships
    )
    assert found_order_customer_rel is True


def test_build_prompt_schema_context(engine):
    context = engine.build_prompt_schema_context("Show top 5 customers by spend")
    assert "TARGET DATABASE DIALECT" in context
    assert "customers" in context
    assert "FOREIGN KEY RELATIONSHIPS" in context

