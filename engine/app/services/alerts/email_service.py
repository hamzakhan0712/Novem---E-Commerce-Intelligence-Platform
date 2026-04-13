"""
Automated email alert service — sends digest emails when anomalies are detected.

Uses SMTP configuration from config/email_config.json.
The SMTP password is stored encrypted via Fernet; all other fields are plaintext.
"""

import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import CONFIG_DIR
from app.core.database import get_sqlite_connection
from app.core.encryption import encrypt_json, decrypt_json
from app.services.insights.insight_engine import detect_anomalies, get_recommended_actions
from app.services.insights.health_score import calculate_health_score

logger = logging.getLogger(__name__)

_CONFIG_PATH = CONFIG_DIR / "email_config.json"


def _load_email_config() -> dict | None:
    """Load SMTP config from file, decrypting the password."""
    if not _CONFIG_PATH.exists():
        logger.warning("Email config not found at %s", _CONFIG_PATH)
        return None
    with open(_CONFIG_PATH) as f:
        config = json.load(f)

    # Decrypt the password if it's stored as an encrypted token
    encrypted_pw = config.get("smtp_password_encrypted")
    if encrypted_pw:
        try:
            pw_data = decrypt_json(encrypted_pw)
            config["smtp_password"] = pw_data.get("password", "")
        except Exception:
            logger.error("Failed to decrypt SMTP password — config may be corrupted")
            return None
        config.pop("smtp_password_encrypted", None)
    return config


def get_email_config() -> dict:
    """Return current email config (without password) for frontend display."""
    config = _load_email_config()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "smtp_host": config.get("smtp_host", ""),
        "smtp_port": config.get("smtp_port", 587),
        "smtp_user": config.get("smtp_user", ""),
        "from_name": config.get("from_name", "NOVEM"),
        "from_email": config.get("from_email", ""),
        "use_tls": config.get("use_tls", True),
    }


def save_email_config(
    smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str,
    from_name: str, from_email: str, use_tls: bool = True,
) -> dict:
    """Save SMTP config to file with encrypted password."""
    encrypted_pw = encrypt_json({"password": smtp_password})
    config = {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password_encrypted": encrypted_pw,
        "from_name": from_name,
        "from_email": from_email,
        "use_tls": use_tls,
    }
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    return {"saved": True}


def test_email_connection() -> dict:
    """Test SMTP connection without sending."""
    config = _load_email_config()
    if not config:
        return {"success": False, "error": "Email not configured"}

    try:
        if config.get("use_tls", True):
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=10)
        server.login(config["smtp_user"], config["smtp_password"])
        server.quit()
        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_anomaly_digest(store_id: str, recipient_email: str, period: str = "7d") -> dict:
    """Build and send an anomaly digest email for a store."""
    config = _load_email_config()
    if not config:
        return {"sent": False, "error": "Email not configured"}

    # Gather intelligence
    anomalies = detect_anomalies(store_id, period)
    actions = get_recommended_actions(store_id, period)
    health = calculate_health_score(store_id, period)

    if not anomalies and not actions:
        return {"sent": False, "reason": "No anomalies or actions to report"}

    # Build HTML email
    html = _build_digest_html(anomalies, actions, health, period)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"NOVEM Alert Digest — {len(anomalies)} anomalies detected"
    msg["From"] = f"{config.get('from_name', 'NOVEM')} <{config['from_email']}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(html, "html"))

    try:
        if config.get("use_tls", True):
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=15)
        server.login(config["smtp_user"], config["smtp_password"])
        server.send_message(msg)
        server.quit()

        # Log the send
        _log_email_send(store_id, recipient_email, len(anomalies), len(actions))

        return {
            "sent": True,
            "anomalies_reported": len(anomalies),
            "actions_reported": len(actions),
            "health_score": health.get("overall_score") if health else None,
        }
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return {"sent": False, "error": str(e)}


def get_email_history(store_id: str, limit: int = 20) -> list[dict]:
    """Return recent email send history."""
    conn = get_sqlite_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            anomaly_count INTEGER,
            action_count INTEGER,
            sent_at TEXT NOT NULL
        )
    """)
    rows = conn.execute(
        "SELECT * FROM email_log WHERE store_id = ? ORDER BY sent_at DESC LIMIT ?",
        (store_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def _log_email_send(store_id: str, recipient: str, anomaly_count: int, action_count: int) -> None:
    conn = get_sqlite_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            anomaly_count INTEGER,
            action_count INTEGER,
            sent_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO email_log (store_id, recipient, anomaly_count, action_count, sent_at) VALUES (?, ?, ?, ?, ?)",
        (store_id, recipient, anomaly_count, action_count, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def _build_digest_html(anomalies: list, actions: list, health: dict, period: str) -> str:
    """Build HTML email body for the anomaly digest."""
    score = health.get("overall_score", "N/A") if health else "N/A"
    label = health.get("label", "") if health else ""

    anomaly_rows = ""
    for a in anomalies[:10]:
        color = "#ff4d4f" if a.get("severity") == "high" else "#fa8c16" if a.get("severity") == "medium" else "#1677ff"
        anomaly_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0">{a.get('date', '')}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0">{a.get('metric', '')}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;color:{color};font-weight:600">
                {a.get('direction', '').upper()} (Z={a.get('z_score', 0):.1f})
            </td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0">{a.get('message', '')}</td>
        </tr>"""

    action_rows = ""
    for act in actions[:5]:
        action_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;font-weight:600">{act.get('title', '')}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0">{act.get('description', '')}</td>
            <td style="padding:8px;border-bottom:1px solid #f0f0f0;color:#52c41a">
                &#x20B9;{act.get('impact_dollars', 0):,.0f}
            </td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto">
        <div style="background:#1a1a2e;padding:20px;text-align:center;border-radius:8px 8px 0 0">
            <h1 style="color:#52c41a;margin:0;font-size:24px">NOVEM Alert Digest</h1>
            <p style="color:#aaa;margin:4px 0 0;font-size:13px">Period: {period} | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>

        <div style="padding:20px;background:#fff;border:1px solid #e8e8e8">
            <div style="text-align:center;margin-bottom:20px">
                <div style="font-size:48px;font-weight:700;color:#1a1a2e">{score}</div>
                <div style="font-size:14px;color:#666">Business Health Score — {label}</div>
            </div>

            <h2 style="color:#1a1a2e;border-bottom:2px solid #52c41a;padding-bottom:8px">
                Anomalies Detected ({len(anomalies)})
            </h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f7f7f7">
                    <th style="padding:8px;text-align:left">Date</th>
                    <th style="padding:8px;text-align:left">Metric</th>
                    <th style="padding:8px;text-align:left">Signal</th>
                    <th style="padding:8px;text-align:left">Detail</th>
                </tr>
                {anomaly_rows}
            </table>

            <h2 style="color:#1a1a2e;border-bottom:2px solid #52c41a;padding-bottom:8px;margin-top:24px">
                Recommended Actions ({len(actions)})
            </h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f7f7f7">
                    <th style="padding:8px;text-align:left">Action</th>
                    <th style="padding:8px;text-align:left">Description</th>
                    <th style="padding:8px;text-align:left">Potential Impact</th>
                </tr>
                {action_rows}
            </table>
        </div>

        <div style="background:#f7f7f7;padding:12px;text-align:center;font-size:11px;color:#999;border-radius:0 0 8px 8px">
            Sent by NOVEM E-Commerce Intelligence Platform — all data processed locally
        </div>
    </body>
    </html>
    """


# ── Transactional email helpers ─────────────────────────────────────────


def _send_transactional(recipient: str, subject: str, html_body: str) -> bool:
    """Send a transactional email. Returns True on success, False on failure."""
    config = _load_email_config()
    if not config:
        logger.debug("Email not configured — skipping transactional send")
        return False

    if not recipient:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.get('from_name', 'NOVEM')} <{config['from_email']}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        if config.get("use_tls", True):
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=15)
        server.login(config["smtp_user"], config["smtp_password"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.warning("Transactional email failed: %s", e)
        return False


def _wrap_email(title: str, body_content: str) -> str:
    """Wrap content in the standard NOVEM email template."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
        <div style="background:#1a1a2e;padding:20px;text-align:center;border-radius:8px 8px 0 0">
            <h1 style="color:#52c41a;margin:0;font-size:24px">NOVEM</h1>
            <p style="color:#aaa;margin:4px 0 0;font-size:13px">E-Commerce Intelligence Platform</p>
        </div>
        <div style="padding:24px;background:#fff;border:1px solid #e8e8e8">
            <h2 style="color:#1a1a2e;margin:0 0 16px">{title}</h2>
            {body_content}
            <p style="margin:20px 0 0;font-size:12px;color:#999">{now_str}</p>
        </div>
        <div style="background:#f7f7f7;padding:12px;text-align:center;font-size:11px;color:#999;border-radius:0 0 8px 8px">
            Sent by NOVEM — all data processed locally on your machine
        </div>
    </body>
    </html>
    """


def send_welcome_email(recipient: str, user_name: str) -> bool:
    """Send a welcome email after initial setup."""
    body = f"""
    <p style="font-size:15px;line-height:1.6">Hi {user_name},</p>
    <p style="font-size:14px;line-height:1.6;color:#555">
        Welcome to <strong>NOVEM</strong>! Your account has been set up successfully.
        You can now import your e-commerce data and start exploring dashboards,
        customer analytics, forecasting, and AI-powered insights — all running
        locally on your machine.
    </p>
    <p style="font-size:14px;line-height:1.6;color:#555">
        Get started by importing your order data from the <strong>Import Data</strong> section.
    </p>
    """
    return _send_transactional(recipient, "Welcome to NOVEM", _wrap_email("Welcome to NOVEM!", body))


def send_login_alert_email(recipient: str, user_name: str) -> bool:
    """Send a login notification email."""
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    body = f"""
    <p style="font-size:14px;line-height:1.6;color:#555">
        Hi {user_name}, a login to your NOVEM workspace was detected on <strong>{now_str}</strong>.
    </p>
    <p style="font-size:14px;line-height:1.6;color:#555">
        If this was you, no action is needed. If you did not perform this login,
        please change your password immediately from <strong>Settings → Security</strong>.
    </p>
    """
    return _send_transactional(recipient, "NOVEM — Login Alert", _wrap_email("Login Detected", body))


def send_password_change_email(recipient: str, user_name: str) -> bool:
    """Send a password change notification email."""
    body = f"""
    <p style="font-size:14px;line-height:1.6;color:#555">
        Hi {user_name}, your NOVEM password was changed successfully.
    </p>
    <p style="font-size:14px;line-height:1.6;color:#555">
        If you did not make this change, please reset your password using the
        security question from the login screen.
    </p>
    """
    return _send_transactional(recipient, "NOVEM — Password Changed", _wrap_email("Password Changed", body))


def send_export_email(recipient: str, user_name: str, report_name: str) -> bool:
    """Send an email notification when a report is exported."""
    body = f"""
    <p style="font-size:14px;line-height:1.6;color:#555">
        Hi {user_name}, your report <strong>{report_name}</strong> has been exported successfully.
    </p>
    <p style="font-size:14px;line-height:1.6;color:#555">
        You can find the exported file in your designated export folder.
    </p>
    """
    return _send_transactional(recipient, f"NOVEM — Report Exported: {report_name}", _wrap_email("Report Exported", body))


def send_alert_email(recipient: str, user_name: str, alert_title: str, alert_message: str) -> bool:
    """Send a generic alert email for important system events."""
    body = f"""
    <p style="font-size:14px;line-height:1.6;color:#555">Hi {user_name},</p>
    <div style="background:#fff7e6;border-left:4px solid #fa8c16;padding:12px 16px;margin:12px 0;border-radius:0 4px 4px 0">
        <strong style="color:#ad6800">{alert_title}</strong>
        <p style="margin:8px 0 0;color:#555;font-size:13px">{alert_message}</p>
    </div>
    <p style="font-size:14px;line-height:1.6;color:#555">
        Review your dashboard for more details.
    </p>
    """
    return _send_transactional(recipient, f"NOVEM Alert — {alert_title}", _wrap_email("Alert Notification", body))
