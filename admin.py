"""Admin callbacks: stats, users, toggle plus/limit, ban, payments, broadcast."""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import db
from keyboards import admin_kb, back_kb, admin_user_kb
from utils import admin_user_text, esc
from config import ADMIN_IDS


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    q = update.callback_query
    data = q.data
    tg_id = q.from_user.id

    if tg_id not in ADMIN_IDS:
        return False

    # ── Admin panel ──
    if data == "admin":
        await q.edit_message_text("👑 Админ-панель:", parse_mode="HTML", reply_markup=admin_kb())
        return True

    # ── Stats ──
    if data == "astats":
        stats = await db.get_stats()
        out = (
            f"<b>📊 Статистика</b>\n\n"
            f"👥 Всего: <b>{stats.get('total', 0)}</b>\n"
            f"⭐ Plus: <b>{stats.get('plus', 0)}</b>\n"
            f"🗂 WL активных: <b>{stats.get('wl_users', 0)}</b>\n"
            f"📱 Устройств: <b>{stats.get('devs', 0)}</b>\n"
            f"🟢 Онлайн (час): <b>{stats.get('online', 0)}</b>\n"
            f"📅 За 24ч: <b>{stats.get('today', 0)}</b>"
        )
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=admin_kb())
        return True

    # ── User list ──
    if data == "ausers":
        users = await db.get_users_list(10)
        out = "<b>👥 Пользователи</b>"
        kb_rows = []
        for u in users:
            icon = "⭐" if u.get("is_plus") else "🆓"
            last = "—"
            if u.get("last_seen"):
                try:
                    from datetime import datetime
                    dt = datetime.strptime(str(u["last_seen"])[:19], "%Y-%m-%d %H:%M:%S")
                    last = dt.strftime("%d.%m %H:%M")
                except Exception:
                    pass
            out += f"\n\n{icon} <b>{esc(u['username'])}</b>\n└ Посл.акт: {last}"
            kb_rows.append([InlineKeyboardButton(
                f"{icon} {esc(u['username'])}", callback_data=f"auser_{u['id']}")])
        kb_rows.append([InlineKeyboardButton("🔙 Назад", callback_data="admin")])
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb_rows))
        return True

    # ── User detail ──
    if data.startswith("auser_"):
        uid = int(data[len("auser_"):])
        u = await db.get_user_by_id(uid)
        if not u:
            await q.answer("Пользователь не найден", show_alert=True)
            return True
        devs = await db.get_devices(uid, deleted=False)
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Toggle Plus ──
    if data.startswith("atoggle_plus_"):
        uid = int(data[len("atoggle_plus_"):])
        new_val = await db.toggle_plus(uid)
        if new_val is None:
            await q.answer("Не найден", show_alert=True)
            return True
        await q.answer("Plus выдан на 30 дней" if new_val else "Plus снят", show_alert=True)
        u = await db.get_user_by_id(uid)
        devs = await db.get_devices(uid, deleted=False)
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Toggle device limit ──
    if data.startswith("atoggle_limit_"):
        uid = int(data[len("atoggle_limit_"):])
        new_val = await db.toggle_limit(uid)
        if new_val is None:
            await q.answer("Не найден", show_alert=True)
            return True
        await q.answer("Лимит снят" if new_val else "Лимит включён", show_alert=True)
        u = await db.get_user_by_id(uid)
        devs = await db.get_devices(uid, deleted=False)
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Ban (toggle plus) ──
    if data.startswith("aban_"):
        uid = int(data[len("aban_"):])
        new_val = await db.toggle_plus(uid)
        if new_val is None:
            await q.answer("Не найден", show_alert=True)
            return True
        await q.answer("Забанен" if new_val == 0 else "Разбанен", show_alert=True)
        u = await db.get_user_by_id(uid)
        devs = await db.get_devices(uid, deleted=False)
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Payments ──
    if data.startswith("apayments_"):
        uid = int(data[len("apayments_"):])
        u = await db.get_user_by_id(uid)
        if not u:
            await q.answer("Не найден", show_alert=True)
            return True

        payments = await db.get_store_payments(u["username"])
        out = f"<b>💰 Платежи @{esc(u['username'])}</b>"
        if not payments:
            out += "\n\nНет платежей."
        else:
            for p in payments:
                icon = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(p.get("status"), "❓")
                out += f"\n\n{icon} {p.get('amount', 0):.0f} ₽ — {esc(p.get('app_title', ''))}"
                dt = str(p.get("created_at", ""))[:10]
                if dt:
                    out += f"\n   <small>{dt}</small>"
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=back_kb(f"auser_{uid}"))
        return True

    # ── Broadcast ──
    if data == "abroadcast":
        context.user_data["awaiting_broadcast"] = True
        await q.message.reply_text(
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте сообщение для рассылки всем Plus-юзерам.\n\n"
            "/cancel для отмены.",
            parse_mode="HTML",
        )
        await q.answer()
        return True

    return False


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.pop("awaiting_broadcast", False):
        return

    tg_id = update.effective_user.id
    if tg_id not in ADMIN_IDS:
        return

    msg_text = update.message.text or update.message.caption or ""
    if not msg_text:
        return

    targets = await db.get_broadcast_targets()
    if not targets:
        await update.message.reply_text("Нет пользователей с chat_id.")
        return

    sent, failed = 0, 0
    for t in targets:
        try:
            await context.bot.send_message(
                chat_id=t["chat_id"],
                text=f"📢 <b>Zotus++</b>\n\n{msg_text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await update.message.reply_text(
        f"📢 Рассылка завершена.\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"
    )
