"""
Unit tests for the SQL Validation and Safety Engine.
Verifies AST checks, destructive keyword rejection, injection defense, and LIMIT enforcement.
"""

import pytest
from backend.database import initialize_database
from backend.validator import SQLValidator, SQLValidationError


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database()


@pytest.fixture
def validator():
    return SQLValidator(max_limit=100)


def test_valid_select_query(validator):
    sql = "SELECT id, first_name, email FROM customers WHERE country = 'USA'"
    result = validator.validate_and_prepare(sql, allowed_tables={"customers"}, enforce_explain=True)
    assert result["is_valid"] is True
    assert "LIMIT 100" in result["sanitized_sql"].upper()


def test_reject_drop_table(validator):
    sql = "DROP TABLE customers;"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql)
    assert "destructive" in str(exc.value).lower() or "drop" in str(exc.value).lower()


def test_reject_delete_statement(validator):
    sql = "DELETE FROM orders WHERE total_amount > 100"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql)
    assert "destructive" in str(exc.value).lower() or "delete" in str(exc.value).lower()


def test_reject_update_statement(validator):
    sql = "UPDATE products SET price = 0.0 WHERE id = 1"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql)
    assert "destructive" in str(exc.value).lower() or "update" in str(exc.value).lower()


def test_reject_insert_statement(validator):
    sql = "INSERT INTO categories (name) VALUES ('Hacking')"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql)
    assert "destructive" in str(exc.value).lower() or "insert" in str(exc.value).lower()


def test_reject_multiple_stacked_statements(validator):
    sql = "SELECT * FROM customers; DROP TABLE orders;"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql)
    assert "multiple sql statements" in str(exc.value).lower() or "destructive" in str(exc.value).lower()


def test_enforce_limit_capping(validator):
    # If query has LIMIT 5000, validator should cap to max_limit (100)
    sql = "SELECT * FROM products LIMIT 5000"
    result = validator.validate_and_prepare(sql, allowed_tables={"products"}, enforce_explain=True)
    assert "LIMIT 100" in result["sanitized_sql"].upper()
    assert result["limit_enforced"] is True


def test_respect_smaller_limit(validator):
    # If query already has LIMIT 5, validator should keep 5
    sql = "SELECT * FROM products LIMIT 5"
    result = validator.validate_and_prepare(sql, allowed_tables={"products"}, enforce_explain=True)
    assert "LIMIT 5" in result["sanitized_sql"].upper()
    assert result["limit_value"] == 5


def test_table_whitelist_unauthorized_table(validator):
    sql = "SELECT * FROM secret_passwords"
    with pytest.raises(SQLValidationError) as exc:
        validator.validate_and_prepare(sql, allowed_tables={"customers", "orders"}, enforce_explain=False)
    assert "unauthorized" in str(exc.value).lower() or "non-existent" in str(exc.value).lower()


def test_allow_cte_queries(validator):
    sql = """
    WITH high_spenders AS (
        SELECT customer_id, SUM(total_amount) as total FROM orders GROUP BY customer_id
    )
    SELECT * FROM high_spenders
    """
    result = validator.validate_and_prepare(sql, allowed_tables={"orders", "high_spenders"}, enforce_explain=True)
    assert result["is_valid"] is True

