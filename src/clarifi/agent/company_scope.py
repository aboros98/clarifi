"""Company scoping — resolves current user's companies for data isolation.

All financial tools use this to filter data per user.
Prevents cross-user data leakage.
"""

import logging

from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.db.session import get_async_session
from clarifi.models.user_profile import UserCompanyLink, UserProfile

logger = logging.getLogger(__name__)

async def get_user_company_ids() -> list[str]:
    """Get ALL company_ids the current user has access to.

    Returns list of company IDs. Financial tools use this to filter
    with `WHERE company_id IN (...)`.
    """
    uid = current_user_id.get()

    async with get_async_session() as session:
        # Get all companies linked to this user
        links = (await session.execute(
            select(UserCompanyLink.company_id).where(
                UserCompanyLink.user_id == uid,
            )
        )).scalars().all()

        if links:
            return list(links)

        # Fallback: user profile's active company
        profile = (await session.execute(
            select(UserProfile.company_id).where(
                UserProfile.user_id == uid,
            )
        )).scalar_one_or_none()

        if profile:
            return [profile]

        # No profile found — no access to any data
        return []
