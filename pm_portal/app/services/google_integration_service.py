"""Google Integration Service for Gmail and Google Drive via OAuth2 REST APIs."""

import base64
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request
import mimetypes
from app.config import WORKING_DIR

logger = logging.getLogger(__name__)

# Credential Paths
GMAIL_CREDENTIALS_FILE = Path.home() / '.gmail-mcp' / 'credentials.json'
GMAIL_CLIENT_SECRETS_FILE = Path.home() / '.gmail-mcp' / 'gcp-oauth.keys.json'

GDRIVE_CREDENTIALS_FILE = Path.home() / '.gemini' / 'credentials' / 'gdrive-token.json'
GDRIVE_CLIENT_SECRETS_FILE = Path.home() / '.gemini' / 'credentials' / 'gcp-oauth.keys.json'


def _refresh_oauth_token(credentials_path: Path, client_secrets_path: Path) -> str:
    """Refresh Google OAuth2 access token if expired and write updated token back."""
    if not credentials_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file chứng thực OAuth tại {credentials_path}")
    
    with open(credentials_path, "r", encoding="utf-8") as f:
        creds_data = json.load(f)
    
    current_token = creds_data.get("access_token", "")
    refresh_token = creds_data.get("refresh_token", "")
    expiry_date = creds_data.get("expiry_date", 0)
    
    # If expiry_date is in epoch milliseconds, check if it's still valid with a 2-minute safety buffer
    now_ms = int(time.time() * 1000)
    if current_token and expiry_date and (expiry_date - now_ms > 120_000):
        return current_token
    
    # Need refresh
    if not refresh_token:
        if current_token:
            return current_token
        raise ValueError(f"Không tìm thấy refresh_token trong {credentials_path}")
    
    # Read client credentials
    client_id = ""
    client_secret = ""
    if client_secrets_path.exists():
        with open(client_secrets_path, "r", encoding="utf-8") as f:
            secret_data = json.load(f)
            installed = secret_data.get("installed") or secret_data.get("web") or secret_data
            client_id = installed.get("client_id", "")
            client_secret = installed.get("client_secret", "")
    
    # Make token refresh request
    token_url = "https://oauth2.googleapis.com/token"
    post_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    encoded_data = urllib.parse.urlencode(post_data).encode("utf-8")
    req = urllib.request.Request(token_url, data=encoded_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            refresh_resp = json.loads(resp.read().decode("utf-8"))
            new_access_token = refresh_resp.get("access_token")
            expires_in = refresh_resp.get("expires_in", 3600)
            
            # Update credentials file
            creds_data["access_token"] = new_access_token
            creds_data["expiry_date"] = int((time.time() + expires_in) * 1000)
            with open(credentials_path, "w", encoding="utf-8") as f:
                json.dump(creds_data, f, indent=2)
            
            logger.info("Successfully refreshed OAuth token for %s", credentials_path.name)
            return new_access_token
    except Exception as exc:
        logger.warning("Token refresh warning: %s. Falling back to current token.", exc)
        return current_token


def get_gmail_access_token() -> str:
    """Get active access token for Gmail API."""
    return _refresh_oauth_token(GMAIL_CREDENTIALS_FILE, GMAIL_CLIENT_SECRETS_FILE)


def get_drive_access_token() -> str:
    """Get active access token for Google Drive API."""
    return _refresh_oauth_token(GDRIVE_CREDENTIALS_FILE, GDRIVE_CLIENT_SECRETS_FILE)


def _resolve_attachment_path(file_path_str: str) -> Optional[Path]:
    """Resolve file path whether absolute, relative, or just filename across project directories."""
    cleaned = file_path_str.strip().strip('"').strip("'")
    if not cleaned:
        return None
    p = Path(cleaned)
    if p.exists() and p.is_file():
        return p

    # Search in Working Directory subfolders
    working_dir = WORKING_DIR
    candidates = [
        working_dir / p.name,
        working_dir / "Ho So Du An" / "Yeu Cau Thanh Toan" / p.name,
        working_dir / "Ho So Du An" / "Nghiem Thu" / p.name,
        working_dir / "Ho So Du An" / "Xuat Kho" / p.name,
        working_dir / "Ho So Du An" / "Bao Gia" / p.name,
        working_dir / "Bieu Mau" / p.name,
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return cand

    # Query SQLite database by file_name
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM documents WHERE file_name = ? OR file_name LIKE ?", (p.name, f"%{p.name}%"))
        row = cursor.fetchone()
        conn.close()
        if row and row["file_path"]:
            db_path = Path(row["file_path"])
            if db_path.exists() and db_path.is_file():
                return db_path
    except Exception as err:
        logger.debug("Database attachment lookup exception: %s", err)

    # Recursive check in Ho So Du An
    ho_so_dir = working_dir / "Ho So Du An"
    if ho_so_dir.exists():
        for found in ho_so_dir.rglob(p.name):
            if found.is_file():
                return found

    return None


def build_raw_email(
    to: List[str],
    subject: str,
    body_text: str,
    html_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> str:
    """Build base64url encoded RFC 2822 email message with resolved file attachments."""
    message = MIMEMultipart("mixed")
    message["Subject"] = subject
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)
    
    body_container = MIMEMultipart("alternative")
    part_text = MIMEText(body_text, "plain", "utf-8")
    body_container.attach(part_text)
    
    if html_body:
        part_html = MIMEText(html_body, "html", "utf-8")
        body_container.attach(part_html)
        
    message.attach(body_container)
    
    # Attach files if provided
    if attachments:
        for file_spec in attachments:
            resolved_p = _resolve_attachment_path(file_spec)
            if resolved_p and resolved_p.is_file():
                try:
                    with open(resolved_p, "rb") as af:
                        file_data = af.read()
                        
                    mtype, _ = mimetypes.guess_type(resolved_p.name)
                    if mtype and "/" in mtype:
                        maintype, subtype = mtype.split("/", 1)
                    else:
                        maintype, subtype = "application", "octet-stream"
                        
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    
                    # RFC 2231 attachment encoding for full Unicode support (Vietnamese / Chinese)
                    # Passing filename as keyword argument prevents Python from corrupting header
                    part.add_header("Content-Disposition", "attachment", filename=resolved_p.name)
                    part.set_param("name", resolved_p.name)
                    
                    message.attach(part)
                    logger.info("Successfully attached file to email: %s (%d bytes)", resolved_p.name, len(file_data))
                except Exception as ex:
                    logger.warning("Could not attach file %s: %s", resolved_p, ex)
            else:
                logger.warning("Attachment file could not be found: %s", file_spec)
    
    raw_bytes = message.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii")


def create_gmail_draft(
    to: List[str],
    subject: str,
    body_text: str,
    html_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a new draft email in the user's connected Gmail account."""
    token = get_gmail_access_token()
    raw_encoded = build_raw_email(
        to=to,
        subject=subject,
        body_text=body_text,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        attachments=attachments
    )
    
    url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
    payload = json.dumps({"message": {"raw": raw_encoded}}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        draft_id = result.get("id")
        return {
            "status": "success",
            "draft_id": draft_id,
            "message_id": result.get("message", {}).get("id"),
            "gmail_url": "https://mail.google.com/mail/u/0/#drafts",
            "message": f"Đã tạo bản nháp email thành công trên Gmail (Mã thư nháp: {draft_id})!"
        }


def send_gmail_message(
    to: List[str],
    subject: str,
    body_text: str,
    html_body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Send an email directly through the connected Gmail account."""
    token = get_gmail_access_token()
    raw_encoded = build_raw_email(
        to=to,
        subject=subject,
        body_text=body_text,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        attachments=attachments
    )
    
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    payload = json.dumps({"raw": raw_encoded}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        message_id = result.get("id")
        return {
            "status": "success",
            "message_id": message_id,
            "message": f"Đã gửi email đề nghị thanh toán thành công (Message ID: {message_id})!"
        }


def search_drive_files(query: str, page_size: int = 15) -> List[Dict[str, Any]]:
    """Search files in the connected Google Drive account."""
    token = get_drive_access_token()
    
    escaped_query = query.replace("'", "\\'")
    if query.strip():
        q_expr = f"name contains '{escaped_query}' and trashed = false"
    else:
        q_expr = "trashed = false"
        
    params = {
        "q": q_expr,
        "fields": "files(id, name, mimeType, size, webViewLink, webContentLink, modifiedTime)",
        "pageSize": page_size,
        "orderBy": "modifiedTime desc"
    }
    url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        files = result.get("files", [])
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "mime_type": f.get("mimeType"),
                "size_bytes": f.get("size", "0"),
                "web_view_link": f.get("webViewLink", ""),
                "modified_time": f.get("modifiedTime", "")
            }
            for f in files
        ]
