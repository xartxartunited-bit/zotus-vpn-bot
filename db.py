"""HTTP API client for Zotus++ and Store databases via bot-db.php."""
import aiohttp

API_URL = "https://vpn.zotus.ru/plus/api/bot-db.php"
API_SECRET = "твой_пароль"


async def _call(action: str, data: dict | None = None) -> dict:
    payload = {"secret": API_SECRET, "action": action, "data": data or {}}
    async with aiohttp.ClientSession() as sess:
        async with sess.post(API_URL, json=payload, timeout=15) as resp:
            return await resp.json()


# ─── Users ───────────────────────────────────────────────────────────────

async def find_user(tg_id: int) -> dict | None:
    r = await _call("find_user", {"tg_id": tg_id})
    return r.get("user") if r.get("ok") else None

async def find_user_by_tg(tg_username: str) -> dict | None:
    r = await _call("find_user_by_tg", {"tg_username": tg_username})
    return r.get("user") if r.get("ok") else None

async def find_user_by_username(username: str) -> dict | None:
    r = await _call("find_user_by_username", {"username": username})
    return r.get("user") if r.get("ok") else None

async def create_user(username: str, tg_id: int, tg_username: str = "",
                      chat_id: int = 0) -> int | None:
    r = await _call("create_user", {
        "username": username, "tg_id": tg_id,
        "tg_username": tg_username, "chat_id": chat_id,
    })
    return r.get("user_id") if r.get("ok") else None

async def update_chat_id(user_id: int, chat_id: int) -> None:
    await _call("update_chat_id", {"user_id": user_id, "chat_id": chat_id})

async def update_telegram(user_id: int, tg_id: int, tg_username: str = "",
                          chat_id: int = 0) -> None:
    await _call("update_telegram", {
        "user_id": user_id, "tg_id": tg_id,
        "tg_username": tg_username, "chat_id": chat_id,
    })

async def update_password(user_id: int, pw_hash: str) -> None:
    await _call("update_password", {"user_id": user_id, "hash": pw_hash})

async def update_last_seen(user_id: int) -> None:
    await _call("update_last_seen", {"user_id": user_id})

async def update_avatar(user_id: int, avatar: str) -> None:
    await _call("update_avatar", {"user_id": user_id, "avatar": avatar})

async def get_user_by_id(user_id: int) -> dict | None:
    r = await _call("get_user_by_id", {"user_id": user_id})
    return r.get("user") if r.get("ok") else None

async def get_wl_limit(username: str) -> int:
    r = await _call("get_wl_limit", {"username": username})
    return r.get("wl_device_limit", 2) if r.get("ok") else 2

# ─── Devices ─────────────────────────────────────────────────────────────

async def get_devices(user_id: int, deleted: bool = False) -> list[dict]:
    r = await _call("get_devices", {"user_id": user_id, "deleted": 1 if deleted else 0})
    return r.get("devices", []) if r.get("ok") else []

async def get_device_count(user_id: int, sub_type: str = "plus") -> int:
    r = await _call("get_device_count", {"user_id": user_id, "sub_type": sub_type})
    return r.get("count", 0) if r.get("ok") else 0

async def get_active_count(user_id: int) -> int:
    r = await _call("get_active_count", {"user_id": user_id})
    return r.get("count", 0) if r.get("ok") else 0

async def delete_device(user_id: int, device_id: str) -> None:
    await _call("delete_device", {"user_id": user_id, "device_id": device_id})

async def restore_device(user_id: int, device_id: str) -> None:
    await _call("restore_device", {"user_id": user_id, "device_id": device_id})

# ─── Streaks ─────────────────────────────────────────────────────────────

async def get_streak(user_id: int) -> dict:
    r = await _call("get_streak", {"user_id": user_id})
    return r.get("streak", {"current_streak": 0, "max_streak": 0}) if r.get("ok") else {"current_streak": 0, "max_streak": 0}

# ─── Admin ───────────────────────────────────────────────────────────────

async def get_stats() -> dict:
    r = await _call("get_stats")
    return r if r.get("ok") else {}

async def get_users_list(limit: int = 10) -> list[dict]:
    r = await _call("get_users_list", {"limit": limit})
    return r.get("users", []) if r.get("ok") else []

async def toggle_plus(user_id: int) -> int | None:
    r = await _call("toggle_plus", {"user_id": user_id})
    return r.get("new_value") if r.get("ok") else None

async def toggle_limit(user_id: int) -> int | None:
    r = await _call("toggle_limit", {"user_id": user_id})
    return r.get("new_value") if r.get("ok") else None

async def get_broadcast_targets() -> list[dict]:
    r = await _call("get_broadcast_targets")
    return r.get("targets", []) if r.get("ok") else []

async def get_expiring_users(days: int) -> list[dict]:
    r = await _call("get_expiring_users", {"days": days})
    return r.get("users", []) if r.get("ok") else []

async def get_pending_payments() -> list[dict]:
    r = await _call("get_pending_payments")
    return r.get("payments", []) if r.get("ok") else []

# ─── Store ───────────────────────────────────────────────────────────────

async def get_store_user(username: str) -> dict | None:
    r = await _call("get_store_user", {"username": username})
    return r.get("user") if r.get("ok") else None

async def create_store_user(username: str, tg_id: int = 0,
                            tg_username: str = "") -> int | None:
    r = await _call("create_store_user", {
        "username": username, "tg_id": tg_id, "tg_username": tg_username,
    })
    return r.get("user_id") if r.get("ok") else None

async def get_balance(username: str) -> float | None:
    r = await _call("get_balance", {"username": username})
    return r.get("balance") if r.get("ok") else None

async def get_store_payments(username: str) -> list[dict]:
    r = await _call("get_store_payments", {"username": username})
    return r.get("payments", []) if r.get("ok") else []
