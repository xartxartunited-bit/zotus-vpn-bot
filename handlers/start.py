"""/start handler — registration and profile display."""
import asyncio
import aiohttp
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db import zotuspp, store, fetch_one, execute, fetch_all, fetch_val
from keyboards import main_kb
from utils import profile_text, esc
from config import ADMIN_IDS, VPN_DOMAIN, AVATAR_UPLOAD_URL, AVATAR_UPLOAD_KEY
from yookassa import create_store_user, get_store_user

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    if not tg_user:
        return

    chat_id = update.effective_chat.id
    tg_id = tg_user.id
    tg_username = tg_user.username or ""
    is_admin = tg_id in ADMIN_IDS

    pp = zotuspp()
    st = store()

    # 1) Find user by telegram_id
    user = await fetch_one(pp, "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))

    # 2) Fallback: find by @username
    if not user and tg_username:
        user = await fetch_one(pp, "SELECT * FROM users WHERE telegram = %s", (tg_username,))

    # 3) New user — register
    if not user:
        username = tg_username or f"tg{tg_id}"
        # Ensure uniqueness
        ex = await fetch_val(pp, "SELECT id FROM users WHERE username = %s", (username,))
        if ex:
            username = f"{username}_{tg_id}"
        await execute(pp,
            "INSERT INTO users (username, password, telegram, telegram_id, chat_id, is_plus, created_at) "
            "VALUES (%s, NULL, %s, %s, %s, 0, NOW())",
            (username, tg_username or None, tg_id, chat_id))
        uid = await fetch_val(pp, "SELECT LAST_INSERT_ID()")
        user = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))

        # Create in Store DB too
        store_ex = await get_store_user(username)
        if not store_ex:
            await create_store_user(username, tg_id, tg_username)

        # Download Telegram avatar in background
        asyncio.create_task(_download_tg_avatar(tg_id, uid))

        await update.message.reply_text(
            f"👋 <b>Добро пожаловать, {esc(username)}!</b>\n\n"
            f"Ваш аккаунт создан. Пароль не установлен — управление через бота.\n\n"
            + profile_text(user, 0, 0, 2, None, {"current_streak": 0, "max_streak": 0}),
            parse_mode="HTML",
            reply_markup=main_kb(False, is_admin),
        )
        return

    # 4) Existing user — update chat_id and show profile
    await execute(pp, "UPDATE users SET chat_id = %s WHERE id = %s", (chat_id, user["id"]))
    user["chat_id"] = chat_id

    # Update telegram_id if missing
    if not user.get("telegram_id"):
        await execute(pp, "UPDATE users SET telegram_id = %s WHERE id = %s", (tg_id, user["id"]))

    # Update username if it was a tg username match
    if not user.get("telegram") and tg_username:
        await execute(pp, "UPDATE users SET telegram = %s WHERE id = %s", (tg_username, user["id"]))

    # Sync to Store
    store_ex = await get_store_user(user["username"])
    if not store_ex:
        await create_store_user(user["username"], tg_id, tg_username)

    # Counts
    plus_count = await fetch_val(pp,
        "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0 AND sub_type = 'plus'",
        (user["id"],)) or 0
    wl_count = await fetch_val(pp,
        "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0 AND sub_type = 'wl'",
        (user["id"],)) or 0
    wl_limit = int(user.get("wl_device_limit", 2) or 2)

    # Streak
    streak = await fetch_one(pp,
        "SELECT current_streak, max_streak FROM user_streaks WHERE user_id = %s",
        (user["id"],)) or {"current_streak": 0, "max_streak": 0}

    # Balance from Store
    bal = await fetch_val(st, "SELECT balance FROM users WHERE username = %s", (user["username"],))

    await update.message.reply_text(
        profile_text(user, plus_count, wl_count, wl_limit, bal, streak),
        parse_mode="HTML",
        reply_markup=main_kb(bool(user.get("is_plus")), is_admin),
    )


async def _download_tg_avatar(tg_id: int, user_id: int) -> None:
    """Download user's Telegram profile photo and upload to vpn.zotus.ru."""
    try:
        # Get user profile photos
        from config import BOT_TOKEN
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, params={"user_id": tg_id, "limit": 1}, timeout=10) as resp:
                data = await resp.json()

        photos = (data.get("result", {}) or {}).get("photos", [])
        if not photos:
            return

        file_id = photos[0][-1]["file_id"]

        # Get file path
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id}, timeout=10
            ) as resp:
                data = await resp.json()

        file_path = data["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        # Download file
        async with aiohttp.ClientSession() as sess:
            async with sess.get(file_url, timeout=15) as resp:
                file_bytes = await resp.read()

        # Upload via PHP API
        form = aiohttp.FormData()
        form.add_field("key", AVATAR_UPLOAD_KEY)
        form.add_field("user_id", str(user_id))
        form.add_field("file", file_bytes, filename=f"tg_avatar_{user_id}.jpg",
                       content_type="image/jpeg")

        async with aiohttp.ClientSession() as sess:
            async with sess.post(AVATAR_UPLOAD_URL, data=form, timeout=15) as resp:
                pass

    except Exception:
        logger.exception("Avatar download failed")
