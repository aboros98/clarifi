"""Onboarding API — first-time company setup."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from clarifi.api.chat import _extract_user_id
from clarifi.db.session import get_async_session
from clarifi.models.company import Company, CompanyRole
from clarifi.models.user_profile import UserProfile

router = APIRouter(prefix="/api", tags=["onboarding"])


class OnboardingRequest(BaseModel):
    company_name: str
    trade_name: str = ""
    tax_id: str = ""
    registration_number: str = ""
    address: str = ""
    city: str = ""
    country_code: str = "RO"
    bank_accounts: list[dict] = []
    user_name: str
    user_role: str = "owner"


class OnboardingStatus(BaseModel):
    onboarded: bool
    company_name: str | None = None
    user_name: str | None = None
    user_role: str | None = None


@router.get("/onboarding/status")
async def check_onboarding(request: Request) -> OnboardingStatus:
    """Check if current user has completed onboarding."""
    user_id = _extract_user_id(request)

    async with get_async_session() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()

        if not profile or not profile.onboarded_at:
            return OnboardingStatus(onboarded=False)

        company = await session.get(Company, profile.company_id)
        return OnboardingStatus(
            onboarded=True,
            company_name=company.legal_name if company else None,
            user_name=profile.display_name,
            user_role=profile.role,
        )


@router.post("/onboarding")
async def onboard(request: Request, body: OnboardingRequest):
    """First-time setup: create company + user profile."""
    user_id = _extract_user_id(request)
    now = datetime.now(timezone.utc)

    async with get_async_session() as session:
        # Check if already onboarded
        existing = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if existing and existing.onboarded_at:
            raise HTTPException(status_code=400, detail="Already onboarded")

        # Check if company with same tax_id exists
        company = None
        if body.tax_id:
            company = (await session.execute(
                select(Company).where(Company.tax_id == body.tax_id, Company.is_deleted == False)
            )).scalar_one_or_none()

        if not company:
            company = Company(
                legal_name=body.company_name,
                trade_name=body.trade_name or body.company_name,
                tax_id=body.tax_id or None,
                registration_number=body.registration_number or None,
                role=CompanyRole.OWN_COMPANY,
                address=body.address or None,
                city=body.city or None,
                country_code=body.country_code,
                bank_accounts=body.bank_accounts or None,
                name_variants=[body.company_name, body.trade_name] if body.trade_name else [body.company_name],
            )
            session.add(company)
            await session.flush()

        # Create or update user profile
        if existing:
            existing.company_id = company.id
            existing.display_name = body.user_name
            existing.role = body.user_role
            existing.onboarded_at = now
            profile_id = existing.id
        else:
            profile = UserProfile(
                user_id=user_id,
                company_id=company.id,
                display_name=body.user_name,
                role=body.user_role,
                onboarded_at=now,
            )
            session.add(profile)
            await session.flush()
            profile_id = profile.id

    return {
        "status": "onboarded",
        "company_id": company.id,
        "company_name": company.legal_name,
        "profile_id": profile_id,
        "user_name": body.user_name,
    }


async def get_company_context(user_id: str) -> str:
    """Get company context string for system prompt injection.
    Returns empty string if user not onboarded."""
    async with get_async_session() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()

        if not profile or not profile.onboarded_at:
            return ""

        company = await session.get(Company, profile.company_id)
        if not company:
            return ""

    parts = [f"## Company Context\nYou are serving **{company.legal_name}**"]
    if company.tax_id:
        parts.append(f"(CUI: {company.tax_id})")
    parts.append(f"\nUser: **{profile.display_name}** (role: {profile.role})")
    if company.city:
        parts.append(f"\nLocation: {company.city}, {company.country_code or 'RO'}")
    if company.bank_accounts and isinstance(company.bank_accounts, list):
        ibans = [ba.get("iban", "") for ba in company.bank_accounts if ba.get("iban")]
        if ibans:
            parts.append(f"\nBank accounts: {', '.join(ibans)}")

    return " ".join(parts[:2]) + "".join(parts[2:])
