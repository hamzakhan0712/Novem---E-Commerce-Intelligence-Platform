import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import DATA_DIR, LOG_LEVEL


def setup_logging() -> None:
    """Configure root logger with console + rotating file handler."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler (already added by default — clear first)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file handler → data/engine.log
    log_dir = Path(DATA_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "engine.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
