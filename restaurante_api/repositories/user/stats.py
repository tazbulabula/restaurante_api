"""User Stats - Métodos estatísticos e agregações."""

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import func, select

from restaurante_api.models.user import User, UserType

from .base import UserBaseRepository


class UserStatsMixin:
    """Mixin com métodos estatísticos."""

    async def count_by_user_type(self) -> Dict[str, int]:
        stats = {}
        for user_type in UserType:
            count = await self.count(user_type=user_type, deleted_at=None)
            stats[user_type.value] = count
        return stats

    async def get_user_type_distribution(self) -> List[Dict[str, Any]]:
        query = (
            select(User.user_type, func.count(User.id).label('count'))
            .where(User.deleted_at.is_(None))
            .group_by(User.user_type)
        )

        result = await self._session.execute(query)
        return [
            {'user_type': row[0].value, 'count': row[1]}
            for row in result.all()
        ]

    async def get_average_user_age_days(self) -> float:
        users = await self.get_active_users()
        if not users:
            return 0.0

        now = datetime.utcnow()
        ages = [
            (now - user.created_at).days for user in users if user.created_at
        ]
        return sum(ages) / len(ages) if ages else 0.0


class UserStatsRepository(UserBaseRepository, UserStatsMixin):
    """Repository focado em estatísticas."""

    pass
