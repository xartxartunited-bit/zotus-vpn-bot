"""User activity tracking: last_seen and streak updates."""
from db import zotuspp, execute, fetch_one


async def track_activity(user_id: int) -> None:
    """Update last_seen and user_streaks for a user."""
    pp = zotuspp()
    await execute(pp,
        "UPDATE users SET last_seen = NOW() WHERE id = %s", (user_id,))


async def get_user_by_tg(tg_id: int) -> dict | None:
    """Find user by telegram_id."""
    from db import fetch_one, zotuspp
    return await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
