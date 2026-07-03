"""Text command handlers: /status, /devices, /buy, /link, /cancel."""
from telegram import Update
from telegram.ext import ContextTypes

from db import zotuspp, store, fetch_one, execute, fetch_all, fetch_val
from keyboards import main_kb, back_kb, devices_kb
from utils import profile_text, device_text, esc
from config import ADMIN_IDS, STORE_URL
from handlers.callbacks import _profile_text, _show_devices


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    is_admin = tg_id in ADMIN_IDS
    user = await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
    if not user:
        await update.message.reply_text("Аккаунт не привязан. /start")
        return
    await update.message.reply_text(
        await _profile_text(user),
        parse_mode="HTML",
        reply_markup=main_kb(bool(user.get("is_plus")), is_admin),
    )


async def devices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    user = await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
    if not user:
        await update.message.reply_text("Аккаунт не привязан. /start")
        return

    pp = zotuspp()
    uid = user["id"]
    is_unl = bool(user.get("no_device_limit"))
    devs = await fetch_all(pp,
        "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = 0 ORDER BY last_seen DESC",
        (uid,))
    out = f"<b>📱 Устройства ({len(devs)}" + ("♾" if is_unl else "/3") + ")</b>"
    if not devs:
        out += "\n\nНет активных устройств."
        kb = back_kb()
    else:
        for i, d in enumerate(devs, 1):
            out += f"\n\n{device_text(d, i, show_type=True)}"
        dkb = devices_kb(devs, "dev_del", restore=False)
        rows = list(dkb.inline_keyboard) + [[
            __import__("telegram").InlineKeyboardButton("📊 Статус", callback_data="status")
        ]]
        from telegram import InlineKeyboardMarkup
        kb = InlineKeyboardMarkup(rows)

    await update.message.reply_text(out, parse_mode="HTML", reply_markup=kb)


async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    user = await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
    store_url = f"{STORE_URL}/app/zotus-plus"
    out = (
        "<b>⭐ Zotus++</b>\n\n"
        "• 100 ₽ / месяц\n• 249 ₽ / 3 месяца\n• 479 ₽ / 6 месяцев\n"
        "❄️ Цена фиксирована навсегда\n\n"
        f"🔗 <a href='{store_url}'>Купить на сайте</a>"
    )
    if user:
        out += f"\n\nВаш логин: <b>{esc(user['username'])}</b>"
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Перейти к покупке", url=store_url)
    ]])
    await update.message.reply_text(out, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: /link <b>ваш_логин</b>",
            parse_mode="HTML",
        )
        return

    login = args[0].lstrip("@")
    tg_user = update.effective_user
    tg_id = tg_user.id
    tg_username = tg_user.username or ""

    if not tg_username:
        await update.message.reply_text(
            "У вас не установлен @username в Telegram. Установите в настройках профиля."
        )
        return

    pp = zotuspp()
    # Check if user exists
    user = await fetch_one(pp, "SELECT * FROM users WHERE username = %s", (login,))
    if not user:
        await update.message.reply_text(
            f"❌ Логин <b>{esc(login)}</b> не найден. Проверьте правильность.",
            parse_mode="HTML",
        )
        return

    if user.get("telegram") and user["telegram"] != tg_username:
        await update.message.reply_text(
            f"❌ Этот аккаунт уже привязан к @{esc(user['telegram'])}. Обратитесь в поддержку.",
            parse_mode="HTML",
        )
        return

    await execute(pp,
        "UPDATE users SET telegram = %s, telegram_id = %s, chat_id = %s WHERE username = %s",
        (tg_username, tg_id, update.effective_chat.id, login))
    await update.message.reply_text(
        f"✅ Аккаунт <b>{esc(login)}</b> привязан!\n\n/start",
        parse_mode="HTML",
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("state", None)
    context.user_data.pop("promo_code", None)
    context.user_data.pop("payment_amount", None)
    context.user_data.pop("payment_tier", None)
    context.user_data.pop("wl_extra", None)
    await update.message.reply_text("Действие отменено.")
