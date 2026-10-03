"""
Integration tests for the complete AI SQL Assistant Pipeline.
"""

import pytest
from backend.database import initialize_database
from backend.pipeline import AISQLPipeline


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database()


@pytest.fixture
def pipeline():
    return AISQLPipeline()


def test_pipeline_customer_query(pipeline):
    res = pipeline.process_query("Show the top 5 customers by total spending")
    assert res["status"] == "success"
    assert "sanitized_sql" in res
    assert "SELECT" in res["sanitized_sql"].upper()
    assert res["execution"]["row_count"] > 0
    assert len(res["execution"]["columns"]) > 0
    assert len(res["natural_answer"]) > 0


def test_pipeline_category_revenue(pipeline):
    res = pipeline.process_query("Which product categories generated the most revenue?")
    assert res["status"] == "success"
    assert res["execution"]["row_count"] > 0
    assert "category_name" in res["execution"]["columns"] or "name" in res["execution"]["columns"]


def test_pipeline_blocks_destructive_query(pipeline):
    res = pipeline.process_query("DROP TABLE customers;")
    assert res["status"] == "validation_error"
    assert "error" in res

