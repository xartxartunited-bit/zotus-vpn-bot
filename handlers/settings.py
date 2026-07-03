"""Settings handlers: password change (ConversationHandler)."""
import bcrypt
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import hashlib
import base64
import os

from db import zotuspp, fetch_one, execute
from keyboards import cancel_kb

AWAIT_PASSWORD = 1


async def chpass_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback: user clicked 'Change/Set password'."""
    q = update.callback_query
    await q.answer()

    tg_id = q.from_user.id
    user = await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))
    if not user:
        await q.edit_message_text("Аккаунт не привязан.", parse_mode="HTML")
        return ConversationHandler.END

    has_pw = bool(user.get("password") and user["password"] is not None)
    action = "смены" if has_pw else "установки"

    context.user_data["chpass_uid"] = user["id"]

    await q.edit_message_text(
        f"🔑 <b>{'Смена' if has_pw else 'Установка'} пароля</b>\n\n"
        f"Отправьте новый пароль (минимум 4 символа).\n\n"
        f"/cancel для отмены.",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    return AWAIT_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new password text."""
    pw = update.message.text.strip()
    if len(pw) < 4:
        await update.message.reply_text(
            "Пароль слишком короткий (мин. 4 символа). Попробуйте снова или /cancel.",
            reply_markup=cancel_kb(),
        )
        return AWAIT_PASSWORD

    uid = context.user_data.pop("chpass_uid", None)
    if not uid:
        await update.message.reply_text("Ошибка сессии. /start")
        return ConversationHandler.END

    import hashlib
    phash = _make_hash(pw)
    await execute(zotuspp(), "UPDATE users SET password = %s WHERE id = %s", (phash, uid))
    await update.message.reply_text(
        f"✅ Пароль изменён!\n\nДлина: {len(pw)} симв.",
        reply_markup=None,
    )
    return ConversationHandler.END


async def cancel_chpass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("chpass_uid", None)
    await update.message.reply_text("❌ Смена пароля отменена.")
    return ConversationHandler.END


async def cancel_chpass_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    context.user_data.pop("chpass_uid", None)
    await q.edit_message_text("❌ Смена пароля отменена.", parse_mode="HTML")
    return ConversationHandler.END


def _make_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def password_conv_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(chpass_start, pattern="^chpass_start$")],
        states={
            AWAIT_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password),
                CommandHandler("cancel", cancel_chpass),
                CallbackQueryHandler(cancel_chpass_cb, pattern="^cancel_state$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_chpass)],
    )
