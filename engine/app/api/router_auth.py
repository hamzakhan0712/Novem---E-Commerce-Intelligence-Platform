"""
Authentication API router — local single-user auth with bcrypt + session tokens.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_sqlite_connection
from app.models.common import ApiResponse
from app.services.alerts.email_service import (
    send_welcome_email,
    send_login_alert_email,
    send_password_change_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# ── Request / Response Models ───────────────────────────────────────────


class SetupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = None
    password: str = Field(..., min_length=8, max_length=128)
    avatar_seed: str | None = None
    avatar_photo: str | None = None
    currency: str = "INR"
    region: str = "IN"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    fiscal_year_start: str = "january"
    security_question: str | None = None
    security_answer: str | None = None


class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    avatar_seed: str | None = None
    avatar_photo: str | None = None
    currency: str | None = None
    region: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    fiscal_year_start: str | None = None


class ForgotPasswordRequest(BaseModel):
    security_answer: str = Field(..., min_length=1)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Helpers ─────────────────────────────────────────────────────────────


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


SESSION_TTL = timedelta(hours=24)

# In-memory rate limiter for login attempts
_login_attempts: dict[str, list[datetime]] = {}
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_WINDOW = timedelta(minutes=15)


def _check_rate_limit(ip: str = "local") -> None:
    """Raise HTTP 429 if too many failed login attempts."""
    now = datetime.now(timezone.utc)
    attempts = _login_attempts.get(ip, [])
    # Purge old attempts outside the lockout window
    attempts = [t for t in attempts if now - t < _LOCKOUT_WINDOW]
    _login_attempts[ip] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {_LOCKOUT_WINDOW.total_seconds() // 60:.0f} minutes.",
        )


def _record_failed_attempt(ip: str = "local") -> None:
    _login_attempts.setdefault(ip, []).append(datetime.now(timezone.utc))


def _create_session() -> str:
    conn = get_sqlite_connection()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = (now + SESSION_TTL).isoformat()
    conn.execute(
        "INSERT INTO sessions (token, created_at, expires_at) VALUES (?, ?, ?)",
        (token, now.isoformat(), expires_at),
    )
    conn.commit()
    return token


def _invalidate_sessions() -> None:
    conn = get_sqlite_connection()
    conn.execute("DELETE FROM sessions")
    conn.commit()


def _is_valid_session(token: str) -> bool:
    conn = get_sqlite_connection()
    row = conn.execute("SELECT token, expires_at FROM sessions WHERE token = ?", (token,)).fetchone()
    if row is None:
        return False
    expires_at = row["expires_at"] if "expires_at" in row.keys() else None
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return False
        except (ValueError, TypeError):
            pass
    return True


def _get_profile_row():
    conn = get_sqlite_connection()
    return conn.execute("SELECT * FROM user_profile WHERE id = 'default'").fetchone()


def _profile_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "avatar_seed": row["avatar_seed"],
        "avatar_photo": row["avatar_photo"] if "avatar_photo" in row.keys() else None,
        "currency": row["currency"],
        "region": row["region"],
        "date_format": row["date_format"],
        "fiscal_year_start": row["fiscal_year_start"],
        "timezone": row["timezone"],
        "security_question": row["security_question"] if "security_question" in row.keys() else None,
        "email_verified": bool(row["email_verified"]) if "email_verified" in row.keys() else False,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/status")
def auth_status() -> ApiResponse:
    """Check whether setup is complete and return user + password policy."""
    row = _get_profile_row()
    is_setup_complete = bool(row and row["is_setup_complete"])

    data: dict = {"is_setup_complete": is_setup_complete}
    if is_setup_complete and row:
        data["user"] = _profile_to_dict(row)
        conn = get_sqlite_connection()
        policy_row = conn.execute(
            "SELECT value FROM settings WHERE key = 'password_policy'"
        ).fetchone()
        data["password_policy"] = policy_row["value"] if policy_row else "every_start"

    return ApiResponse(success=True, data=data)


@router.post("/setup")
def setup_profile(req: SetupRequest) -> ApiResponse:
    """First-time profile creation. Sets password and marks setup complete."""
    conn = get_sqlite_connection()
    row = conn.execute("SELECT is_setup_complete FROM user_profile WHERE id = 'default'").fetchone()
    if row and row["is_setup_complete"]:
        raise HTTPException(status_code=400, detail="Setup already completed")

    now = datetime.now(timezone.utc).isoformat()
    password_hash = _hash_password(req.password)
    security_answer_hash = _hash_password(req.security_answer) if req.security_answer else None

    conn.execute(
        """
        INSERT OR REPLACE INTO user_profile
        (id, name, email, avatar_seed, avatar_photo, currency, region, timezone, date_format,
         fiscal_year_start, password_hash, security_question, security_answer_hash,
         is_setup_complete, created_at, updated_at)
        VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            req.name, req.email, req.avatar_seed, req.avatar_photo, req.currency, req.region,
            req.timezone, req.date_format, req.fiscal_year_start,
            password_hash, req.security_question, security_answer_hash,
            now, now,
        ),
    )
    conn.commit()

    token = _create_session()
    profile = _get_profile_row()

    logger.info("User profile setup completed")

    # Send welcome email (non-blocking, best-effort)
    if req.email:
        try:
            send_welcome_email(req.email, req.name)
        except Exception:
            logger.debug("Welcome email could not be sent")

    return ApiResponse(
        success=True,
        data={"token": token, "user": _profile_to_dict(profile)},
    )


@router.post("/login")
def login(req: LoginRequest) -> ApiResponse:
    """Verify password and create a session."""
    _check_rate_limit()

    row = _get_profile_row()
    if not row or not row["is_setup_complete"]:
        raise HTTPException(status_code=400, detail="Setup not completed")

    if not row["password_hash"] or not _verify_password(req.password, row["password_hash"]):
        _record_failed_attempt()
        raise HTTPException(status_code=401, detail="Incorrect password")

    _invalidate_sessions()
    token = _create_session()

    logger.info("User logged in")

    # Send login alert email (non-blocking, best-effort)
    if row["email"]:
        try:
            send_login_alert_email(row["email"], row["name"])
        except Exception:
            logger.debug("Login alert email could not be sent")

    return ApiResponse(
        success=True,
        data={"token": token, "user": _profile_to_dict(row)},
    )


@router.post("/auto-login")
def auto_login() -> ApiResponse:
    """Create a session without password (for 'never' password policy)."""
    row = _get_profile_row()
    if not row or not row["is_setup_complete"]:
        raise HTTPException(status_code=400, detail="Setup not completed")

    conn = get_sqlite_connection()
    policy_row = conn.execute(
        "SELECT value FROM settings WHERE key = 'password_policy'"
    ).fetchone()
    policy = policy_row["value"] if policy_row else "every_start"

    if policy != "never":
        raise HTTPException(status_code=403, detail="Auto-login not allowed with current password policy")

    _invalidate_sessions()
    token = _create_session()

    logger.info("User auto-logged in (password policy: never)")
    return ApiResponse(
        success=True,
        data={"token": token, "user": _profile_to_dict(row)},
    )


@router.post("/verify")
def verify_session(token: str | None = None) -> ApiResponse:
    """Check whether a session token is valid."""
    if not token or not _is_valid_session(token):
        return ApiResponse(success=True, data={"valid": False})
    return ApiResponse(success=True, data={"valid": True})


@router.post("/lock")
def lock_app() -> ApiResponse:
    """Invalidate all sessions (lock the app)."""
    _invalidate_sessions()
    logger.info("App locked — all sessions cleared")
    return ApiResponse(success=True, data={"locked": True})


@router.patch("/profile")
def update_profile(req: UpdateProfileRequest) -> ApiResponse:
    """Update profile fields (does not change password)."""
    conn = get_sqlite_connection()
    updates: list[str] = []
    params: list = []

    for field in ["name", "email", "avatar_seed", "avatar_photo", "currency", "region",
                   "timezone", "date_format", "fiscal_year_start"]:
        value = getattr(req, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append("default")

    conn.execute(
        f"UPDATE user_profile SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()

    profile = _get_profile_row()
    return ApiResponse(success=True, data=_profile_to_dict(profile))


@router.post("/change-password")
def change_password(req: ChangePasswordRequest) -> ApiResponse:
    """Change password. Requires current password for verification."""
    row = _get_profile_row()
    if not row or not row["password_hash"]:
        raise HTTPException(status_code=400, detail="No password set")

    if not _verify_password(req.current_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = _hash_password(req.new_password)
    conn = get_sqlite_connection()
    conn.execute(
        "UPDATE user_profile SET password_hash = ?, updated_at = ? WHERE id = 'default'",
        (new_hash, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()

    _invalidate_sessions()
    token = _create_session()

    logger.info("Password changed successfully")

    # Send password change notification (non-blocking, best-effort)
    row_updated = _get_profile_row()
    if row_updated and row_updated["email"]:
        try:
            send_password_change_email(row_updated["email"], row_updated["name"])
        except Exception:
            logger.debug("Password change email could not be sent")

    return ApiResponse(success=True, data={"token": token})


@router.get("/security-question")
def get_security_question() -> ApiResponse:
    """Return the security question (no answer) for forgot-password flow."""
    row = _get_profile_row()
    if not row or not row["is_setup_complete"]:
        raise HTTPException(status_code=400, detail="Setup not completed")

    question = row["security_question"] if "security_question" in row.keys() else None
    if not question:
        raise HTTPException(status_code=404, detail="No security question configured")

    return ApiResponse(success=True, data={"security_question": question})


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest) -> ApiResponse:
    """Verify security answer and return a one-time reset token."""
    row = _get_profile_row()
    if not row or not row["is_setup_complete"]:
        raise HTTPException(status_code=400, detail="Setup not completed")

    answer_hash = row["security_answer_hash"] if "security_answer_hash" in row.keys() else None
    if not answer_hash:
        raise HTTPException(status_code=400, detail="No security question configured")

    if not _verify_password(req.security_answer.lower().strip(), answer_hash):
        raise HTTPException(status_code=401, detail="Incorrect answer")

    _invalidate_sessions()
    reset_token = uuid.uuid4().hex
    conn = get_sqlite_connection()
    conn.execute(
        "INSERT INTO sessions (token, created_at) VALUES (?, ?)",
        (f"reset:{reset_token}", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()

    logger.info("Forgot password — reset token issued")
    return ApiResponse(success=True, data={"reset_token": reset_token})


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest) -> ApiResponse:
    """Use a reset token to set a new password."""
    conn = get_sqlite_connection()
    row = conn.execute(
        "SELECT token FROM sessions WHERE token = ?",
        (f"reset:{req.reset_token}",),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")

    new_hash = _hash_password(req.new_password)
    conn.execute(
        "UPDATE user_profile SET password_hash = ?, updated_at = ? WHERE id = 'default'",
        (new_hash, datetime.now(timezone.utc).isoformat()),
    )
    conn.execute("DELETE FROM sessions")
    conn.commit()

    token = _create_session()

    logger.info("Password reset successfully")
    return ApiResponse(success=True, data={"token": token})
