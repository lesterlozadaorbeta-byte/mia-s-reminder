"""Usage stats and limits endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limiter import get_usage_stats
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_my_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's usage stats and limits."""
    return await get_usage_stats(current_user, db)
