"""/start handler — registration and profile display."""
import asyncio
import aiohttp
import logging
from telegram import Update
from telegram.ext import ContextTypes

import db
from keyboards import main_kb
from utils import profile_text, esc
from config import ADMIN_IDS, AVATAR_UPLOAD_URL, AVATAR_UPLOAD_KEY
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

    # 1) Find user by telegram_id
    user = await db.find_user(tg_id)

    # 2) Fallback: find by @username
    if not user and tg_username:
        user = await db.find_user_by_tg(tg_username)

    # 3) New user — register
    if not user:
        username = tg_username or f"tg{tg_id}"
        ex = await db.find_user_by_username(username)
        if ex:
            username = f"{username}_{tg_id}"
        uid = await db.create_user(username, tg_id, tg_username, chat_id)
        if uid:
            user = await db.get_user_by_id(uid)

        # Create in Store DB too
        store_ex = await get_store_user(username)
        if not store_ex:
            await create_store_user(username, tg_id, tg_username)

        # Download Telegram avatar in background
        asyncio.create_task(_download_tg_avatar(tg_id, uid))

        await update.message.reply_text(
            f"👋 <b>Добро пожаловать, {esc(username)}!</b>\n\n"
            f"Ваш аккаунт создан. Пароль не установлен — управление через бота.\n\n"
            + profile_text(user or {}, 0, 0, 2, None, {"current_streak": 0, "max_streak": 0}),
            parse_mode="HTML",
            reply_markup=main_kb(False, is_admin),
        )
        return

    # 4) Existing user — update chat_id and show profile
    await db.update_chat_id(user["id"], chat_id)

    if not user.get("telegram_id"):
        await db.update_telegram(user["id"], tg_id, tg_username or user.get("telegram", ""), chat_id)
    elif not user.get("telegram") and tg_username:
        await db.update_telegram(user["id"], tg_id, tg_username, chat_id)

    # Sync to Store
    store_ex = await get_store_user(user["username"])
    if not store_ex:
        await create_store_user(user["username"], tg_id, tg_username)

    # Counts
    plus_count = await db.get_device_count(user["id"], "plus")
    wl_count = await db.get_device_count(user["id"], "wl")
    wl_limit = await db.get_wl_limit(user["username"])

    # Streak
    streak = await db.get_streak(user["id"])

    # Balance from Store
    bal = await db.get_balance(user["username"])

    await update.message.reply_text(
        profile_text(user, plus_count, wl_count, wl_limit, bal, streak),
        parse_mode="HTML",
        reply_markup=main_kb(bool(user.get("is_plus")), is_admin),
    )


async def _download_tg_avatar(tg_id: int, user_id: int) -> None:
    try:
        from config import BOT_TOKEN
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, params={"user_id": tg_id, "limit": 1}, timeout=10) as resp:
                data = await resp.json()

        photos = (data.get("result", {}) or {}).get("photos", [])
        if not photos:
            return

        file_id = photos[0][-1]["file_id"]
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id}, timeout=10
            ) as resp:
                data = await resp.json()

        file_path = data["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        async with aiohttp.ClientSession() as sess:
            async with sess.get(file_url, timeout=15) as resp:
                file_bytes = await resp.read()

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
