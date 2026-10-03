"""
LLM Client Integration.
Supports OpenAI, Google Gemini, Ollama, LangChain, and an intelligent Mock provider
for seamless offline testing and evaluation.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
import httpx
from backend.config import settings


class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower()

    def generate_sql(self, schema_context: str, natural_query: str) -> str:
        """
        Translates a natural language question into SQL based on the schema context.
        """
        prompt = (
            f"You are an expert SQL analyst. Convert the user's natural language question into a single, "
            f"clean, read-only SQL query matching the database schema provided.\n\n"
            f"{schema_context}\n\n"
            f"User Question: {natural_query}\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"1. Output ONLY the raw SQL query. Do NOT include markdown fences, backticks, or explanatory text.\n"
            f"2. Only write read-only SELECT queries (or WITH...SELECT CTEs).\n"
            f"3. Strictly use the tables and columns present in the schema.\n"
            f"4. Apply sensible aliases and formatting.\n"
            f"SQL Query:"
        )

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            return self._call_openai(prompt)
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            return self._call_gemini(prompt)
        elif self.provider == "ollama":
            return self._call_ollama(prompt)
        else:
            return self._mock_sql_generator(natural_query)

    def synthesize_answer(
        self,
        natural_query: str,
        sql_query: str,
        columns: List[str],
        rows: List[List[Any]],
        row_count: int
    ) -> str:
        """
        Synthesizes the raw tabular SQL execution results into a concise, natural-language business insight.
        """
        # Prepare sample table for context
        preview_rows = rows[:10]
        data_preview = json.dumps({
            "columns": columns,
            "sample_rows": preview_rows,
            "total_rows_returned": row_count
        }, default=str)

        prompt = (
            f"You are a helpful business intelligence assistant.\n"
            f"The user asked: '{natural_query}'\n"
            f"The system executed this SQL: {sql_query}\n"
            f"Query Results:\n{data_preview}\n\n"
            f"Write a concise, professional, and clear 1-3 sentence summary directly answering the user's question "
            f"with specific figures or names from the results. Avoid tech jargon unless relevant."
        )

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            return self._call_openai(prompt)
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            return self._call_gemini(prompt)
        elif self.provider == "ollama":
            return self._call_ollama(prompt)
        else:
            return self._mock_answer_synthesizer(natural_query, columns, rows, row_count)

    # Provider implementations
    def _call_openai(self, prompt: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a specialized SQL generation and analytics assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"-- OpenAI Error: {str(e)}\n" + self._mock_sql_generator(prompt)

    def _call_gemini(self, prompt: str) -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception as e:
            return f"-- Gemini Error: {str(e)}\n" + self._mock_sql_generator(prompt)

    def _call_ollama(self, prompt: str) -> str:
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                return res.json().get("response", "").strip()
        except Exception as e:
            return f"-- Ollama Error: {str(e)}\n" + self._mock_sql_generator(prompt)

    def _mock_sql_generator(self, query: str) -> str:
        """
        Intelligent rule-based generator for zero-configuration testing.
        Covers various analytics patterns for the e-commerce demo dataset.
        """
        raw_clean = query.strip().rstrip(";")
        first_word = raw_clean.split()[0].upper() if raw_clean.split() else ""

        # If user tests raw SQL or destructive commands directly, pass through so validator can catch it
        if first_word in {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "PRAGMA"} or ";" in query:
            return query.strip()

        q = query.lower()

        # 1. Top customers by spend
        if "top" in q and ("customer" in q or "spender" in q or "spending" in q):
            return """
SELECT 
    c.id, 
    c.first_name || ' ' || c.last_name AS customer_name, 
    c.email, 
    c.loyalty_tier, 
    ROUND(CAST(SUM(o.total_amount) AS NUMERIC), 2) AS total_spent,
    COUNT(o.id) AS total_orders
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.status != 'cancelled'
GROUP BY c.id, customer_name, c.email, c.loyalty_tier
ORDER BY total_spent DESC
LIMIT 5;
            """.strip()

        # 2. Category revenue / sales
        if "category" in q or "categories" in q:
            if "rating" in q:
                return """
SELECT 
    c.name AS category_name, 
    ROUND(CAST(AVG(p.rating) AS NUMERIC), 2) AS average_rating,
    COUNT(p.id) AS product_count
FROM categories c
JOIN products p ON c.id = p.category_id
GROUP BY c.name
ORDER BY average_rating DESC;
                """.strip()
            return """
SELECT 
    c.name AS category_name, 
    ROUND(CAST(SUM(oi.quantity * oi.unit_price) AS NUMERIC), 2) AS total_revenue,
    SUM(oi.quantity) AS total_items_sold
FROM categories c
JOIN products p ON c.id = p.category_id
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.status != 'cancelled'
GROUP BY c.name
ORDER BY total_revenue DESC;
            """.strip()

        # 3. Best selling products
        if "product" in q and ("top" in q or "best" in q or "selling" in q or "revenue" in q or "popular" in q):
            return """
SELECT 
    p.id, 
    p.name AS product_name, 
    p.price, 
    p.rating, 
    SUM(oi.quantity) AS total_units_sold, 
    ROUND(CAST(SUM(oi.quantity * oi.unit_price) AS NUMERIC), 2) AS total_revenue
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.status != 'cancelled'
GROUP BY p.id, p.name, p.price, p.rating
ORDER BY total_units_sold DESC
LIMIT 5;
            """.strip()

        # 4. Low stock products
        if "stock" in q or "inventory" in q:
            return """
SELECT 
    p.id, 
    p.name AS product_name, 
    c.name AS category_name, 
    p.stock_quantity, 
    p.price
FROM products p
JOIN categories c ON p.category_id = c.id
WHERE p.stock_quantity < 50
ORDER BY p.stock_quantity ASC;
            """.strip()

        # 5. Orders by status / pending / shipped
        if "status" in q or "pending" in q or "shipped" in q or "cancelled" in q or "delivered" in q:
            return """
SELECT 
    status, 
    COUNT(*) AS order_count, 
    ROUND(CAST(SUM(total_amount) AS NUMERIC), 2) AS total_value,
    ROUND(CAST(AVG(total_amount) AS NUMERIC), 2) AS average_order_value
FROM orders
GROUP BY status
ORDER BY order_count DESC;
            """.strip()

        # 6. Customers who never ordered
        if "never" in q or "haven't" in q or "without" in q:
            return """
SELECT 
    c.id, 
    c.first_name || ' ' || c.last_name AS customer_name, 
    c.email, 
    c.country
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;
            """.strip()

        # 7. Customer geographic distribution
        if "country" in q or "city" in q or "location" in q:
            return """
SELECT 
    country, 
    COUNT(*) AS customer_count,
    COUNT(DISTINCT city) AS cities_count
FROM customers
GROUP BY country
ORDER BY customer_count DESC;
            """.strip()

        # 8. Reviews / ratings
        if "review" in q or "rating" in q or "feedback" in q:
            return """
SELECT 
    p.name AS product_name, 
    r.rating, 
    r.comment, 
    c.first_name || ' ' || c.last_name AS reviewer_name
FROM reviews r
JOIN products p ON r.product_id = p.id
JOIN customers c ON r.customer_id = c.id
ORDER BY r.rating DESC, r.created_at DESC
LIMIT 5;
            """.strip()

        # 9. Recent orders
        if "recent" in q or "latest" in q or "orders" in q:
            return """
SELECT 
    o.id AS order_id, 
    c.first_name || ' ' || c.last_name AS customer_name, 
    o.order_date, 
    o.status, 
    o.total_amount, 
    o.payment_method
FROM orders o
JOIN customers c ON o.customer_id = c.id
ORDER BY o.order_date DESC
LIMIT 10;
            """.strip()

        # Default fallback
        return """
SELECT 
    p.id, 
    p.name AS product_name, 
    c.name AS category, 
    p.price, 
    p.rating, 
    p.stock_quantity
FROM products p
JOIN categories c ON p.category_id = c.id
ORDER BY p.rating DESC
LIMIT 10;
        """.strip()

    def _mock_answer_synthesizer(
        self,
        query: str,
        columns: List[str],
        rows: List[List[Any]],
        row_count: int
    ) -> str:
        """Generates natural language summary for mock mode."""
        if row_count == 0:
            return f"The query executed successfully, but no records matched the criteria for '{query}'."

        first_row = rows[0]
        summary_items = []
        for col, val in zip(columns[:4], first_row[:4]):
            summary_items.append(f"{col}: {val}")

        details = ", ".join(summary_items)
        return (
            f"Found {row_count} matching record(s). "
            f"Top result: {details}."
        )


# Singleton instance
llm_client = LLMClient()
