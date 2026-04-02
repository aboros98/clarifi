"""Integration endpoints — Google Drive OAuth, Telegram webhook."""

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.api.chat import _extract_user_id
from clarifi.config import settings
from clarifi.db.session import get_async_session
from clarifi.models.integration import IntegrationConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# ─── Google Drive ───

DRIVE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DRIVE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_SCOPES = "https://www.googleapis.com/auth/drive.readonly"


@router.get("/drive/auth")
async def drive_auth_redirect():
    """Get the Google Drive OAuth2 authorization URL."""
    if not settings.google_drive_client_id:
        raise HTTPException(status_code=400, detail="Google Drive client_id not configured")

    params = {
        "client_id": settings.google_drive_client_id,
        "redirect_uri": settings.google_drive_redirect_uri,
        "response_type": "code",
        "scope": DRIVE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{DRIVE_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": url}


@router.post("/drive/callback")
async def drive_auth_callback(request: Request):
    """Handle Google Drive OAuth2 callback. Exchanges code for tokens."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            DRIVE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_drive_client_id,
                "client_secret": settings.google_drive_client_secret,
                "redirect_uri": settings.google_drive_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Token exchange failed: {resp.text[:200]}")
        tokens = resp.json()

    # Save tokens to integration_configs (scoped by user)
    async with get_async_session() as session:
        existing = (await session.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.provider == "google_drive",
                IntegrationConfig.user_id == user_id,
            )
        )).scalar_one_or_none()

        if existing:
            existing.config = tokens
            existing.status = "connected"
            existing.connected_at = datetime.now(timezone.utc)
        else:
            session.add(IntegrationConfig(
                provider="google_drive",
                config=tokens,
                status="connected",
                connected_at=datetime.now(timezone.utc),
                user_id=user_id,
            ))

    return {"status": "connected", "provider": "google_drive"}


@router.get("/drive/status")
async def drive_status(request: Request):
    """Check Google Drive connection status for the authenticated user."""
    user_id = _extract_user_id(request)
    current_user_id.set(user_id)

    async with get_async_session() as session:
        config = (await session.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.provider == "google_drive",
                IntegrationConfig.user_id == user_id,
            )
        )).scalar_one_or_none()

    if not config:
        return {"status": "disconnected", "provider": "google_drive"}

    return {
        "status": config.status,
        "provider": "google_drive",
        "connected_at": config.connected_at.isoformat() if config.connected_at else None,
    }


# ─── Telegram ───

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram updates (messages from users)."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot not configured")

    body = await request.json()
    logger.info("Telegram update: %s", body)

    message = body.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return {"ok": True}

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from langchain_core.messages import HumanMessage

    from clarifi.agent.graph import get_graph
    from clarifi.api.chat import extract_ai_response

    now = datetime.now(ZoneInfo("Europe/Bucharest"))
    timestamp = now.strftime("%d.%m.%Y, %H:%M")

    # Handle document/photo uploads
    doc = message.get("document")
    photo = message.get("photo")

    if doc or photo:
        # Download file from Telegram
        file_id = doc["file_id"] if doc else photo[-1]["file_id"]
        file_name = doc.get("file_name", "telegram_upload.pdf") if doc else "telegram_photo.jpg"

        try:
            async with httpx.AsyncClient() as client:
                # Get file path from Telegram
                file_info = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                    params={"file_id": file_id},
                )
                file_path = file_info.json().get("result", {}).get("file_path")

                if file_path:
                    # Download file
                    file_resp = await client.get(
                        f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}",
                    )

                    # Save and process
                    import hashlib
                    from pathlib import Path

                    from clarifi.config import settings as app_settings

                    content = file_resp.content
                    file_hash = hashlib.sha256(content).hexdigest()
                    storage_dir = Path(app_settings.processed_dir)
                    storage_dir.mkdir(parents=True, exist_ok=True)
                    permanent_path = storage_dir / f"{file_hash}_{file_name}"
                    permanent_path.write_bytes(content)

                    # Process via background agent
                    import asyncio

                    from clarifi.api.documents import _background_process

                    asyncio.create_task(
                        _background_process(
                            str(permanent_path), file_name, "", f"telegram-{chat_id}",
                        )
                    )

                    text = f"[{timestamp}] Am primit documentul {file_name}. Il procesez."
                    caption = message.get("caption", "")
                    if caption:
                        text += f" Mentiune: {caption}"
                else:
                    text = f"[{timestamp}] Nu am putut descarca fisierul."
        except Exception:
            logger.exception("Telegram file download failed")
            text = f"[{timestamp}] Eroare la descarcare fisier."

        # Send acknowledgment
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
        return {"ok": True}

    if not text:
        return {"ok": True}

    # Process text message via agent
    text = f"[{timestamp}] {text}"
    graph = await get_graph()
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"thread_id": f"telegram-{chat_id}"}},
        )
        response = extract_ai_response(result) or "Nu am putut genera un raspuns."
    except Exception:
        logger.exception("Telegram agent error")
        response = "A aparut o eroare. Incearca din nou."

    # Send reply
    async with httpx.AsyncClient() as client:
        # Telegram markdown can fail — fallback to plain text
        try:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": response, "parse_mode": "Markdown"},
            )
        except Exception:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": response},
            )

    return {"ok": True}


@router.get("/telegram/status")
async def telegram_status():
    """Check Telegram bot connection status."""
    if not settings.telegram_bot_token:
        return {"status": "disconnected", "provider": "telegram"}


    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
            )
            if resp.status_code == 200:
                bot_info = resp.json().get("result", {})
                return {
                    "status": "connected",
                    "provider": "telegram",
                    "bot_name": bot_info.get("username"),
                }
    except Exception:
        pass

    return {"status": "error", "provider": "telegram"}


@router.post("/telegram/setup")
async def telegram_setup_webhook(request: Request):
    """Set up Telegram webhook URL."""
    body = await request.json()
    webhook_url = body.get("webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Missing webhook_url")
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
            json={"url": f"{webhook_url}/api/integrations/telegram/webhook"},
        )
        return resp.json()
