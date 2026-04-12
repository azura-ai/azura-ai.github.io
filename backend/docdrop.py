"""
DocDrop — WhatsApp & Email Document Receiver
Handles incoming documents/images from WhatsApp (Meta Cloud API) and Email (SendGrid Inbound Parse).
Stores files locally, logs to SQLite, and sends confirmation replies.
"""

import os
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from loguru import logger

try:
    import resend
except ImportError:
    resend = None

# ─── Configuration ───────────────────────────────────────────────────────────

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "azura_docdrop_verify_2026")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
UPLOAD_DIR = Path("uploads")
DB_PATH = "docdrop.db"

router = APIRouter(prefix="/webhook", tags=["DocDrop"])
api_router = APIRouter(prefix="/api", tags=["DocDrop API"])

# ─── Database ────────────────────────────────────────────────────────────────

def init_docdrop_db():
    """Initialize the DocDrop documents database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            sender TEXT,
            filename TEXT,
            file_path TEXT,
            file_size INTEGER DEFAULT 0,
            mime_type TEXT,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'received',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("DocDrop database initialized.")


def log_document(channel: str, sender: str, filename: str, file_path: str,
                 file_size: int = 0, mime_type: str = "", subject: str = "", message: str = ""):
    """Log a received document to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO documents (channel, sender, filename, file_path, file_size, mime_type, subject, message) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (channel, sender, filename, file_path, file_size, mime_type, subject, message)
        )
        conn.commit()
        doc_id = c.lastrowid
        conn.close()
        logger.info(f"Document logged: #{doc_id} [{channel}] {filename} from {sender}")
        return doc_id
    except Exception as e:
        logger.error(f"DB logging error: {e}")
        return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_upload_dirs():
    """Create upload directories if they don't exist."""
    (UPLOAD_DIR / "whatsapp").mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / "email").mkdir(parents=True, exist_ok=True)


def make_safe_filename(original: str) -> str:
    """Generate a timestamped, safe filename."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Keep only safe characters
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in original)
    return f"{ts}_{safe}"


# ─── WhatsApp Webhook ───────────────────────────────────────────────────────

@router.get("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_verify(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    WhatsApp webhook verification (GET).
    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We return the challenge if the token matches.
    """
    logger.info(f"WhatsApp verify: mode={hub_mode}, token={hub_verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully.")
        return hub_challenge or ""
    
    logger.warning("WhatsApp webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_message(request: Request):
    """
    WhatsApp webhook message handler (POST).
    Receives incoming messages with media (images, documents, videos, audio).
    Downloads the media, saves it, and sends a confirmation reply.
    """
    ensure_upload_dirs()

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"WhatsApp webhook received: {body}")

    # Extract message data from Meta webhook payload
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
    except (IndexError, KeyError):
        return {"status": "ok", "detail": "No messages in payload"}

    for msg in messages:
        sender_phone = msg.get("from", "unknown")
        msg_type = msg.get("type", "text")
        msg_id = msg.get("id", "")

        # Handle media messages (image, document, video, audio)
        media_types = ["image", "document", "video", "audio"]
        
        if msg_type in media_types:
            media = msg.get(msg_type, {})
            media_id = media.get("id", "")
            mime_type = media.get("mime_type", "application/octet-stream")
            
            # For documents, Meta provides a filename
            original_filename = media.get("filename", f"{msg_type}_{media_id}")
            if not original_filename or original_filename == f"{msg_type}_{media_id}":
                # Generate filename from mime type
                ext_map = {
                    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                    "video/mp4": ".mp4", "audio/ogg": ".ogg", "audio/mpeg": ".mp3",
                    "application/pdf": ".pdf",
                }
                ext = ext_map.get(mime_type, ".bin")
                original_filename = f"{msg_type}_{media_id}{ext}"

            safe_name = make_safe_filename(original_filename)
            save_path = UPLOAD_DIR / "whatsapp" / safe_name

            # Download media from Meta Graph API
            downloaded = await download_whatsapp_media(media_id, save_path)

            if downloaded:
                file_size = save_path.stat().st_size
                log_document(
                    channel="whatsapp",
                    sender=sender_phone,
                    filename=original_filename,
                    file_path=str(save_path),
                    file_size=file_size,
                    mime_type=mime_type,
                    message=media.get("caption", "")
                )
                # Send confirmation reply
                await send_whatsapp_reply(
                    sender_phone,
                    f"✅ Your Document has been received successfully.\n\n"
                    f"📄 File: {original_filename}\n"
                    f"📦 Size: {file_size / 1024:.1f} KB\n"
                    f"🕐 Received at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                    f"Thank you for using Azura AI DocDrop!"
                )
            else:
                await send_whatsapp_reply(
                    sender_phone,
                    "⚠️ We received your message but couldn't download the file. Please try again."
                )

        elif msg_type == "text":
            # Handle plain text messages
            text_body = msg.get("text", {}).get("body", "")
            logger.info(f"WhatsApp text from {sender_phone}: {text_body}")
            await send_whatsapp_reply(
                sender_phone,
                "👋 Welcome to Azura AI DocDrop!\n\n"
                "Send me any document or image, and I'll confirm receipt.\n\n"
                "Supported: 📄 PDFs, 🖼️ Images, 🎥 Videos, 🎵 Audio files"
            )
        
        # Mark message as read
        await mark_whatsapp_read(msg_id)

    return {"status": "ok"}


async def download_whatsapp_media(media_id: str, save_path: Path) -> bool:
    """Download media from the Meta Graph API using the media ID."""
    if not WHATSAPP_ACCESS_TOKEN:
        logger.warning("WHATSAPP_ACCESS_TOKEN not set. Cannot download media.")
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Get the media URL
            url_resp = await client.get(
                f"https://graph.facebook.com/v21.0/{media_id}",
                headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
            )
            url_resp.raise_for_status()
            media_url = url_resp.json().get("url")

            if not media_url:
                logger.error(f"No URL returned for media {media_id}")
                return False

            # Step 2: Download the actual file
            file_resp = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
            )
            file_resp.raise_for_status()

            save_path.write_bytes(file_resp.content)
            logger.info(f"Media downloaded: {save_path} ({len(file_resp.content)} bytes)")
            return True

    except Exception as e:
        logger.error(f"Media download failed for {media_id}: {e}")
        return False


async def send_whatsapp_reply(to_phone: str, message: str):
    """Send a text reply via WhatsApp Cloud API."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not set. Skipping reply.")
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "text",
                    "text": {"body": message},
                },
            )
            resp.raise_for_status()
            logger.info(f"WhatsApp reply sent to {to_phone}")
    except Exception as e:
        logger.error(f"WhatsApp reply failed to {to_phone}: {e}")


async def mark_whatsapp_read(message_id: str):
    """Mark a WhatsApp message as read."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
    except Exception:
        pass  # Non-critical


# ─── Email Webhook (SendGrid Inbound Parse) ─────────────────────────────────

@router.post("/email")
async def email_inbound(request: Request):
    """
    Email inbound webhook handler.
    Receives POST from SendGrid Inbound Parse (multipart/form-data).
    Extracts sender, subject, body, and attachments.
    """
    ensure_upload_dirs()

    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")

    sender_email = form.get("from", "unknown")
    subject = form.get("subject", "No Subject")
    body_text = form.get("text", "")
    body_html = form.get("html", "")

    logger.info(f"Email received from {sender_email}: {subject}")

    # Extract attachments
    attachment_count = 0
    saved_files = []

    # SendGrid sends attachments as file fields
    # Check for numbered attachments (attachment1, attachment2, etc.)
    for key in form:
        if key.startswith("attachment"):
            attachment = form[key]
            if hasattr(attachment, "filename") and attachment.filename:
                safe_name = make_safe_filename(attachment.filename)
                save_path = UPLOAD_DIR / "email" / safe_name

                content = await attachment.read()
                save_path.write_bytes(content)

                file_size = len(content)
                mime_type = getattr(attachment, "content_type", "application/octet-stream")

                doc_id = log_document(
                    channel="email",
                    sender=str(sender_email),
                    filename=attachment.filename,
                    file_path=str(save_path),
                    file_size=file_size,
                    mime_type=str(mime_type),
                    subject=str(subject),
                    message=str(body_text)[:500]
                )

                saved_files.append(attachment.filename)
                attachment_count += 1
                logger.info(f"Email attachment saved: {save_path} ({file_size} bytes)")

    # If no file attachments but has body, still log it
    if attachment_count == 0:
        log_document(
            channel="email",
            sender=str(sender_email),
            filename="(no attachment)",
            file_path="",
            subject=str(subject),
            message=str(body_text)[:500]
        )

    # Send confirmation reply via Resend
    await send_email_confirmation(str(sender_email), saved_files, str(subject))

    return {
        "status": "ok",
        "attachments_received": attachment_count,
        "files": saved_files
    }


async def send_email_confirmation(to_email: str, files: list, original_subject: str):
    """Send a confirmation email reply via Resend."""
    if not resend or not os.getenv("RESEND_API_KEY"):
        logger.warning("Resend not configured. Skipping email confirmation.")
        return

    try:
        # Clean the sender email (SendGrid format might be "Name <email>")
        clean_email = to_email
        if "<" in to_email and ">" in to_email:
            clean_email = to_email.split("<")[1].split(">")[0]

        file_list = "\n".join(f"  • {f}" for f in files) if files else "  (No attachments)"

        resend.Emails.send({
            "from": "Azura AI DocDrop <onboarding@resend.dev>",
            "to": [clean_email],
            "subject": f"✅ Document Received — Re: {original_subject}",
            "html": f"""
            <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a1a; color: #e0e0e0; padding: 40px; border-radius: 16px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #a78bfa; font-size: 24px; margin: 0;">AZURA<span style="color: #7c3aed;">AI</span></h1>
                    <p style="color: #6b7280; font-size: 12px; margin: 5px 0;">DocDrop — Document Receiver</p>
                </div>
                
                <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(167, 139, 250, 0.05)); padding: 30px; border-radius: 12px; border: 1px solid rgba(124, 58, 237, 0.2);">
                    <h2 style="color: #a78bfa; font-size: 20px; margin: 0 0 15px 0;">✅ Your Document Has Been Received Successfully</h2>
                    <p style="color: #9ca3af; line-height: 1.6;">
                        We have received your email and the following files have been securely stored:
                    </p>
                    <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin: 15px 0; font-family: monospace; font-size: 13px; color: #c4b5fd;">
                        {file_list.replace(chr(10), '<br>')}
                    </div>
                    <p style="color: #6b7280; font-size: 13px;">
                        📧 Original Subject: {original_subject}<br>
                        🕐 Received: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(124, 58, 237, 0.2);">
                    <p style="color: #4b5563; font-size: 12px;">Powered by Azura AI — Document Automation</p>
                    <a href="https://azura-ai.github.io/docdrop.html" style="color: #7c3aed; font-size: 12px;">azura-ai.github.io</a>
                </div>
            </div>
            """
        })
        logger.info(f"Confirmation email sent to {clean_email}")
    except Exception as e:
        logger.error(f"Email confirmation failed: {e}")


# ─── Documents API ───────────────────────────────────────────────────────────

@api_router.get("/documents")
async def list_documents(channel: str = None, limit: int = 50, offset: int = 0):
    """List received documents, optionally filtered by channel."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if channel:
            c.execute(
                "SELECT * FROM documents WHERE channel = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (channel, limit, offset)
            )
        else:
            c.execute(
                "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )

        rows = [dict(row) for row in c.fetchall()]

        # Get total count
        if channel:
            c.execute("SELECT COUNT(*) FROM documents WHERE channel = ?", (channel,))
        else:
            c.execute("SELECT COUNT(*) FROM documents")
        total = c.fetchone()[0]

        conn.close()

        return {
            "status": "ok",
            "total": total,
            "documents": rows
        }
    except Exception as e:
        logger.error(f"Documents list error: {e}")
        return {"status": "error", "total": 0, "documents": []}


@api_router.get("/documents/stats")
async def document_stats():
    """Get document receiving statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM documents")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM documents WHERE channel = 'whatsapp'")
        whatsapp_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM documents WHERE channel = 'email'")
        email_count = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(file_size), 0) FROM documents")
        total_bytes = c.fetchone()[0]

        conn.close()

        return {
            "status": "ok",
            "total_documents": total,
            "whatsapp_documents": whatsapp_count,
            "email_documents": email_count,
            "total_storage_mb": round(total_bytes / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            "status": "ok",
            "total_documents": 0,
            "whatsapp_documents": 0,
            "email_documents": 0,
            "total_storage_mb": 0
        }
