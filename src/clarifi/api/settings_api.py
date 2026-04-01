"""Settings API — read/write app configuration."""

from fastapi import APIRouter

from clarifi.config import settings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def get_settings():
    """Get current application settings (safe subset)."""
    return {
        "llm_model": settings.llm_model,
        "llm_extraction_model": settings.llm_extraction_model,
        "auto_approve_threshold": settings.auto_approve_threshold,
        "alert_cashflow_days": settings.alert_cashflow_days,
        "alert_invoice_due_soon_days": settings.alert_invoice_due_soon_days,
        "alert_contract_expiry_days": settings.alert_contract_expiry_days,
        "freshness_unverified_days": settings.freshness_unverified_days,
        "watch_dir": settings.watch_dir,
        "has_google_api_key": bool(settings.google_api_key and len(settings.google_api_key) > 10),
        "has_drive_credentials": bool(settings.google_drive_client_id),
        "has_telegram_bot": bool(settings.telegram_bot_token),
    }
