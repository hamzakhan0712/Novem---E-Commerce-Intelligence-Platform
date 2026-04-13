"""PyInstaller entry point for the NOVEM compute engine."""

import uvicorn

from app.config import ENGINE_PORT
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=ENGINE_PORT,
        log_level="info",
    )
