"""User activity tracking: last_seen update."""
import db


async def track_activity(user_id: int) -> None:
    await db.update_last_seen(user_id)
