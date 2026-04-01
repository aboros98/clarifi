"""Onboarding API — first-time company setup + multi-company support."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from clarifi.api.chat import _extract_user_id
from clarifi.db.session import get_async_session
from clarifi.models.company import Company, CompanyRole
from clarifi.models.user_profile import UserCompanyLink, UserProfile

router = APIRouter(prefix="/api", tags=["onboarding"])


class CompanyInput(BaseModel):
    company_name: str
    trade_name: str = ""
    tax_id: str = ""
    registration_number: str = ""
    address: str = ""
    city: str = ""
    country_code: str = "RO"
    bank_accounts: list[dict] = []


class OnboardingRequest(BaseModel):
    companies: list[CompanyInput]
    user_name: str
    user_role: str = "owner"


class OnboardingStatus(BaseModel):
    onboarded: bool
    company_name: str | None = None
    companies: list[dict] = []
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

        # Fetch all linked companies
        links = (await session.execute(
            select(UserCompanyLink).where(
                UserCompanyLink.user_id == user_id,
            )
        )).scalars().all()

        companies = []
        active_name = None
        for link in links:
            company = await session.get(Company, link.company_id)
            if company and not company.is_deleted:
                entry = {
                    "id": company.id,
                    "name": company.legal_name,
                    "trade_name": company.trade_name,
                    "tax_id": company.tax_id,
                    "role": link.role,
                    "active": company.id == profile.company_id,
                }
                companies.append(entry)
                if company.id == profile.company_id:
                    active_name = company.legal_name

        # Fallback for users onboarded before multi-company
        if not companies:
            company = await session.get(Company, profile.company_id)
            if company:
                active_name = company.legal_name
                companies = [{
                    "id": company.id,
                    "name": company.legal_name,
                    "trade_name": company.trade_name,
                    "tax_id": company.tax_id,
                    "role": profile.role,
                    "active": True,
                }]

        return OnboardingStatus(
            onboarded=True,
            company_name=active_name,
            companies=companies,
            user_name=profile.display_name,
            user_role=profile.role,
        )


@router.post("/onboarding")
async def onboard(request: Request, body: OnboardingRequest):
    """First-time setup: create companies + user profile.
    Supports multiple companies per user."""
    user_id = _extract_user_id(request)
    now = datetime.now(UTC)

    if not body.companies:
        raise HTTPException(
            status_code=400, detail="At least one company is required",
        )

    async with get_async_session() as session:
        # Check if already onboarded
        existing = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if existing and existing.onboarded_at:
            raise HTTPException(status_code=400, detail="Already onboarded")

        created_companies = []
        for comp in body.companies:
            # Reuse company if same tax_id exists
            company = None
            if comp.tax_id:
                company = (await session.execute(
                    select(Company).where(
                        Company.tax_id == comp.tax_id,
                        Company.is_deleted == False,  # noqa: E712
                    )
                )).scalar_one_or_none()

            if not company:
                company = Company(
                    legal_name=comp.company_name,
                    trade_name=comp.trade_name or comp.company_name,
                    tax_id=comp.tax_id or None,
                    registration_number=comp.registration_number or None,
                    role=CompanyRole.OWN_COMPANY,
                    address=comp.address or None,
                    city=comp.city or None,
                    country_code=comp.country_code,
                    bank_accounts=comp.bank_accounts or None,
                    name_variants=(
                        [comp.company_name, comp.trade_name]
                        if comp.trade_name
                        else [comp.company_name]
                    ),
                )
                session.add(company)
                await session.flush()

            # Create link
            link = UserCompanyLink(
                user_id=user_id,
                company_id=company.id,
                role=body.user_role,
            )
            session.add(link)
            created_companies.append({
                "id": company.id,
                "name": company.legal_name,
            })

        # First company is the active one
        active_company_id = created_companies[0]["id"]

        # Create or update user profile
        if existing:
            existing.company_id = active_company_id
            existing.display_name = body.user_name
            existing.role = body.user_role
            existing.onboarded_at = now
            profile_id = existing.id
        else:
            profile = UserProfile(
                user_id=user_id,
                company_id=active_company_id,
                display_name=body.user_name,
                role=body.user_role,
                onboarded_at=now,
            )
            session.add(profile)
            await session.flush()
            profile_id = profile.id

    return {
        "status": "onboarded",
        "companies": created_companies,
        "active_company_id": active_company_id,
        "profile_id": profile_id,
        "user_name": body.user_name,
    }


@router.post("/onboarding/switch-company/{company_id}")
async def switch_company(request: Request, company_id: str):
    """Switch the active company for the current user."""
    user_id = _extract_user_id(request)

    async with get_async_session() as session:
        # Verify user has link to this company
        link = (await session.execute(
            select(UserCompanyLink).where(
                UserCompanyLink.user_id == user_id,
                UserCompanyLink.company_id == company_id,
            )
        )).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Company not found")

        profile = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile.company_id = company_id

    return {"status": "switched", "active_company_id": company_id}


class UpdateProfileRequest(BaseModel):
    user_name: str | None = None
    user_role: str | None = None


@router.put("/onboarding/profile")
async def update_profile(request: Request, body: UpdateProfileRequest):
    """Update user display name and role."""
    user_id = _extract_user_id(request)

    async with get_async_session() as session:
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        if body.user_name is not None:
            profile.display_name = body.user_name
        if body.user_role is not None:
            profile.role = body.user_role

    return {"status": "updated"}


class AddCompanyRequest(BaseModel):
    company_name: str
    trade_name: str = ""
    tax_id: str = ""
    registration_number: str = ""
    address: str = ""
    city: str = ""
    country_code: str = "RO"
    bank_accounts: list[dict] = []


@router.post("/onboarding/companies")
async def add_company(request: Request, body: AddCompanyRequest):
    """Add a new company to the current user."""
    user_id = _extract_user_id(request)

    async with get_async_session() as session:
        # Reuse if same tax_id
        company = None
        if body.tax_id:
            company = (await session.execute(
                select(Company).where(
                    Company.tax_id == body.tax_id,
                    Company.is_deleted == False,  # noqa: E712
                )
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
            )
            session.add(company)
            await session.flush()

        # Check if link already exists
        existing_link = (await session.execute(
            select(UserCompanyLink).where(
                UserCompanyLink.user_id == user_id,
                UserCompanyLink.company_id == company.id,
            )
        )).scalar_one_or_none()

        if not existing_link:
            link = UserCompanyLink(
                user_id=user_id,
                company_id=company.id,
                role="owner",
            )
            session.add(link)

    return {"status": "added", "company_id": company.id, "name": company.legal_name}


@router.delete("/onboarding/companies/{company_id}")
async def remove_company(request: Request, company_id: str):
    """Remove a company from the current user (soft-delete the link)."""
    user_id = _extract_user_id(request)

    async with get_async_session() as session:
        link = (await session.execute(
            select(UserCompanyLink).where(
                UserCompanyLink.user_id == user_id,
                UserCompanyLink.company_id == company_id,
            )
        )).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Company not found")

        # Don't allow removing the last company
        count = (await session.execute(
            select(UserCompanyLink).where(
                UserCompanyLink.user_id == user_id,
            )
        )).scalars().all()
        if len(count) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Nu poti sterge ultima companie",
            )

        # If removing active company, switch to another
        profile = (await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )).scalar_one_or_none()
        if profile and profile.company_id == company_id:
            others = [c for c in count if c.company_id != company_id]
            if others:
                profile.company_id = others[0].company_id

        session.delete(link)

    return {"status": "removed"}


import re


def _sanitize(text: str) -> str:
    """Strip markdown control characters and limit length for safe prompt injection."""
    if not text:
        return ""
    text = re.sub(r"[#*]", "", text)
    return text[:200].strip()


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

    legal_name = _sanitize(company.legal_name)
    tax_id = _sanitize(company.tax_id) if company.tax_id else ""
    display_name = _sanitize(profile.display_name)
    role = _sanitize(profile.role)

    parts = [f"## Company Context\nYou are serving **{legal_name}**"]
    if tax_id:
        parts.append(f"(CUI: {tax_id})")
    parts.append(
        f"\nUser: **{display_name}** (role: {role})",
    )
    if company.city:
        parts.append(
            f"\nLocation: {company.city}, {company.country_code or 'RO'}",
        )
    if company.bank_accounts and isinstance(company.bank_accounts, list):
        ibans = [
            ba.get("iban", "")
            for ba in company.bank_accounts
            if ba.get("iban")
        ]
        if ibans:
            parts.append(f"\nBank accounts: {', '.join(ibans)}")

    return " ".join(parts[:2]) + "".join(parts[2:])
