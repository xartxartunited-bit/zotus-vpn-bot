"""Text command handlers: /status, /devices, /buy, /link, /cancel."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import db
from keyboards import main_kb, back_kb, devices_kb
from utils import profile_text, device_text, esc
from config import ADMIN_IDS, STORE_URL
from handlers.callbacks import _profile_text


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    is_admin = tg_id in ADMIN_IDS
    user = await db.find_user(tg_id)
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
    user = await db.find_user(tg_id)
    if not user:
        await update.message.reply_text("Аккаунт не привязан. /start")
        return

    uid = user["id"]
    is_unl = bool(user.get("no_device_limit"))
    devs = await db.get_devices(uid, deleted=False)
    out = f"<b>📱 Устройства ({len(devs)}" + ("♾" if is_unl else "/3") + ")</b>"
    if not devs:
        out += "\n\nНет активных устройств."
        kb = back_kb()
    else:
        for i, d in enumerate(devs, 1):
            out += f"\n\n{device_text(d, i, show_type=True)}"
        dkb = devices_kb(devs, "dev_del", restore=False)
        rows = list(dkb.inline_keyboard) + [[
            InlineKeyboardButton("📊 Статус", callback_data="status")
        ]]
        kb = InlineKeyboardMarkup(rows)

    await update.message.reply_text(out, parse_mode="HTML", reply_markup=kb)


async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    user = await db.find_user(tg_id)
    store_url = f"{STORE_URL}/app/zotus-plus"
    out = (
        "<b>⭐ Zotus++</b>\n\n"
        "• 100 ₽ / месяц\n• 249 ₽ / 3 месяца\n• 479 ₽ / 6 месяцев\n"
        "❄️ Цена фиксирована навсегда\n\n"
        f"🔗 <a href='{store_url}'>Купить на сайте</a>"
    )
    if user:
        out += f"\n\nВаш логин: <b>{esc(user['username'])}</b>"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛒 Перейти к покупке", url=store_url)
    ]])
    await update.message.reply_text(out, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /link <b>ваш_логин</b>", parse_mode="HTML")
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

    user = await db.find_user_by_username(login)
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

    await db.update_telegram(user["id"], tg_id, tg_username, update.effective_chat.id)
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
