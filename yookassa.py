"""YooKassa integration via Store bot-api.php."""
import aiohttp
from config import STORE_URL

API_URL = f"{STORE_URL}/yookassa/bot-api.php"
API_SECRET = "твой_пароль"


async def _call(action: str, data: dict | None = None) -> dict:
    payload = {"secret": API_SECRET, "action": action, "data": data or {}}
    async with aiohttp.ClientSession() as sess:
        async with sess.post(API_URL, json=payload, timeout=20) as resp:
            return await resp.json()


async def create_payment(amount_rub: float, zotus_username: str, tier: str,
                         store_user_id: int, wl_extra: bool = False,
                         promo_code: str = "") -> dict | None:
    result = await _call("create_payment", {
        "amount": amount_rub,
        "zotus_username": zotus_username,
        "tier": tier,
        "store_user_id": store_user_id,
        "wl_extra": wl_extra,
        "promo_code": promo_code,
        "app_slug": "zotus-plus",
    })
    if result.get("success"):
        return {"payment_url": result["payment_url"], "purchase_id": result["purchase_id"]}
    return None


async def check_payment(purchase_id: int) -> dict | None:
    result = await _call("check_payment", {"purchase_id": purchase_id})
    if result.get("success"):
        return {"status": result["status"], "purchase_id": purchase_id}
    return None


async def check_promo(code: str, amount: float, user_id: int) -> dict:
    return await _call("check_promo", {"code": code, "amount": amount, "user_id": user_id})


async def get_wl_usernames(store_user_id: int) -> list[str]:
    result = await _call("get_wl_usernames", {"store_user_id": store_user_id})
    if result.get("success"):
        return result.get("usernames", [])
    return []


async def get_payments(store_user_id: int) -> list[dict]:
    result = await _call("get_payments", {"store_user_id": store_user_id})
    if result.get("success"):
        return result.get("payments", [])
    return []


async def get_store_user(login: str) -> dict | None:
    result = await _call("get_store_user", {"login": login})
    if result.get("success"):
        return result["user"]
    return None


async def create_store_user(username: str, tg_id: int | None = None,
                            tg_username: str = "") -> int | None:
    result = await _call("create_store_user", {
        "username": username,
        "telegram_id": str(tg_id) if tg_id else None,
        "telegram": tg_username,
    })
    if result.get("success"):
        return result["id"]
    return None


async def link_store_tg(store_user_id: int, tg_id: int,
                        tg_username: str = "") -> bool:
    result = await _call("link_store_tg", {
        "store_user_id": store_user_id,
        "telegram_id": str(tg_id),
        "telegram": tg_username,
    })
    return result.get("success", False)
