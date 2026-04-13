import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# When frozen (PyInstaller), resolve the project root from the executable
# directory. Otherwise, the project root is the parent of the `app/` package.
if getattr(sys, "frozen", False):
    _PROJECT_ROOT = Path(os.environ.get("NOVEM_ENGINE_DIR", os.path.dirname(sys.executable)))
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENGINE_PORT: int = int(os.getenv("NOVEM_ENGINE_PORT", "44945"))
DATA_DIR: Path = Path(os.getenv("NOVEM_DATA_DIR", str(_PROJECT_ROOT / "data")))
CONFIG_DIR: Path = Path(os.getenv("NOVEM_CONFIG_DIR", str(_PROJECT_ROOT / "config")))
LOG_LEVEL: str = os.getenv("NOVEM_LOG_LEVEL", "info")
OLLAMA_URL: str = os.getenv("NOVEM_OLLAMA_URL", "http://localhost:11434")

DUCKDB_PATH: Path = DATA_DIR / "analytics.duckdb"
SQLITE_PATH: Path = DATA_DIR / "metadata.sqlite"

CORS_ORIGINS: list[str] = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
]
