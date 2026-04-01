"""Integration endpoints — Google Drive OAuth, Telegram webhook."""

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

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

    # Save tokens to integration_configs
    async with get_async_session() as session:
        existing = (await session.execute(
            select(IntegrationConfig).where(IntegrationConfig.provider == "google_drive")
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
            ))

    return {"status": "connected", "provider": "google_drive"}


@router.get("/drive/status")
async def drive_status():
    """Check Google Drive connection status."""
    async with get_async_session() as session:
        config = (await session.execute(
            select(IntegrationConfig).where(IntegrationConfig.provider == "google_drive")
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

    if not text or not chat_id:
        return {"ok": True}

    # Process via agent
    from clarifi.agent.graph import get_graph
    from langchain_core.messages import HumanMessage
    from clarifi.api.chat import extract_ai_response

    graph = await get_graph()
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=text)]},
        config={"configurable": {"thread_id": f"telegram-{chat_id}"}},
    )
    response = extract_ai_response(result)

    # Send reply via Telegram API

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": response, "parse_mode": "Markdown"},
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
