"""
AI SQL Assistant Launcher.
Starts the FastAPI server with auto-reload and prints terminal status.
"""

import sys
import uvicorn
from backend.config import settings
from backend.database import initialize_database, get_dialect_name



def main():
    print(f"[*] Initializing Database...")
    initialize_database()
    dialect = get_dialect_name()
    print(f"[+] Active Database Dialect: {dialect.upper()}")
    print(f"[+] LLM Provider: {settings.LLM_PROVIDER.upper()}")
    print(f"[+] Max Row Limit Guardrail: {settings.MAX_QUERY_ROWS_LIMIT} rows")
    print(f"[*] Web Dashboard & API URL: http://{settings.HOST}:{settings.PORT}")
    print(f"[*] Interactive API Docs:    http://{settings.HOST}:{settings.PORT}/docs")
    print(f"[*] Press CTRL+C to stop the server\n" + "-" * 70)

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()

