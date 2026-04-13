import json
import logging
import os
import stat
import sys

from cryptography.fernet import Fernet

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

_KEY_PATH = DATA_DIR / ".novem_key"
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if _KEY_PATH.exists():
        key = _KEY_PATH.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        _KEY_PATH.write_bytes(key)
        # Restrict file permissions to owner only
        if sys.platform == "win32":
            os.chmod(_KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
        else:
            os.chmod(_KEY_PATH, 0o600)
        logger.info("Generated new encryption key at %s", _KEY_PATH)

    _fernet = Fernet(key)
    return _fernet


def encrypt_json(data: dict) -> str:
    """Encrypt a dict to a Fernet token string."""
    raw = json.dumps(data).encode("utf-8")
    return _get_fernet().encrypt(raw).decode("utf-8")


def decrypt_json(token: str) -> dict:
    """Decrypt a Fernet token string back to a dict."""
    raw = _get_fernet().decrypt(token.encode("utf-8"))
    return json.loads(raw)
