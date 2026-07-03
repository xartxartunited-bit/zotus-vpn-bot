"""Admin callbacks: stats, users, toggle plus/limit, ban, payments, broadcast."""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from db import zotuspp, store, fetch_one, execute, fetch_all, fetch_val
from keyboards import admin_kb, back_kb, admin_user_kb
from utils import admin_user_text, esc
from config import ADMIN_IDS


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin callbacks. Returns True if handled, False otherwise."""
    q = update.callback_query
    data = q.data
    tg_id = q.from_user.id

    if tg_id not in ADMIN_IDS:
        return False

    pp = zotuspp()
    st = store()

    # ── Admin panel ──
    if data == "admin":
        await q.edit_message_text("👑 Админ-панель:", parse_mode="HTML", reply_markup=admin_kb())
        return True

    # ── Stats ──
    if data == "astats":
        total = await fetch_val(pp, "SELECT COUNT(*) FROM users") or 0
        plus = await fetch_val(pp, "SELECT COUNT(*) FROM users WHERE is_plus = 1") or 0
        online = await fetch_val(pp,
            "SELECT COUNT(*) FROM users WHERE last_seen > DATE_SUB(NOW(), INTERVAL 1 HOUR)") or 0
        today = await fetch_val(pp,
            "SELECT COUNT(*) FROM users WHERE last_seen > DATE_SUB(NOW(), INTERVAL 24 HOUR)") or 0
        devs = await fetch_val(pp,
            "SELECT COUNT(*) FROM sub_devices WHERE is_deleted = 0") or 0
        wl_users = await fetch_val(pp,
            "SELECT COUNT(*) FROM users WHERE wl_device_limit > 2") or 0

        out = (
            f"<b>📊 Статистика</b>\n\n"
            f"👥 Всего: <b>{total}</b>\n"
            f"⭐ Plus: <b>{plus}</b>\n"
            f"🗂 WL активных: <b>{wl_users}</b>\n"
            f"📱 Устройств: <b>{devs}</b>\n"
            f"🟢 Онлайн (час): <b>{online}</b>\n"
            f"📅 За 24ч: <b>{today}</b>"
        )
        try:
            ev = await fetch_val(pp,
                "SELECT COUNT(*) FROM user_events WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)")
            if ev:
                out += f"\n📈 Событий: <b>{ev}</b>"
        except Exception:
            pass
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=admin_kb())
        return True

    # ── User list ──
    if data == "ausers":
        users = await fetch_all(pp,
            "SELECT id, username, is_plus, no_device_limit, last_seen "
            "FROM users ORDER BY last_seen DESC LIMIT 10")
        out = "<b>👥 Пользователи</b>"
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        if not u:
            await q.answer("Пользователь не найден", show_alert=True)
            return True
        devs = await fetch_all(pp,
            "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = 0 ORDER BY last_seen DESC",
            (uid,))
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Toggle Plus ──
    if data.startswith("atoggle_plus_"):
        uid = int(data[len("atoggle_plus_"):])
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        if not u:
            await q.answer("Не найден", show_alert=True)
            return True

        new_val = 0 if u.get("is_plus") else 1
        await execute(pp, "UPDATE users SET is_plus = %s WHERE id = %s", (new_val, uid))
        if new_val and not u.get("sub_token"):
            import secrets
            sub_token = secrets.token_hex(24)
            plus_id = f"admin{secrets.token_hex(4)}"
            await execute(pp,
                "UPDATE users SET sub_token = %s, plus_id = %s, subscription_expires = '0000-00-00 00:00:00' WHERE id = %s",
                (sub_token, plus_id, uid))
        if new_val and (not u.get("subscription_expires") or str(u.get("subscription_expires")) in ("0000-00-00 00:00:00", "None", "")):
            await execute(pp,
                "UPDATE users SET subscription_expires = DATE_ADD(NOW(), INTERVAL 30 DAY) WHERE id = %s",
                (uid,))

        await q.answer("Plus выдан на 30 дней" if new_val else "Plus снят", show_alert=True)

        # Refresh
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        devs = await fetch_all(pp,
            "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = 0 ORDER BY last_seen DESC",
            (uid,))
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Toggle device limit ──
    if data.startswith("atoggle_limit_"):
        uid = int(data[len("atoggle_limit_"):])
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        if not u:
            await q.answer("Не найден", show_alert=True)
            return True

        new_val = 0 if u.get("no_device_limit") else 1
        await execute(pp, "UPDATE users SET no_device_limit = %s WHERE id = %s", (new_val, uid))
        await q.answer("Лимит снят" if new_val else "Лимит включён", show_alert=True)

        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        devs = await fetch_all(pp,
            "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = 0 ORDER BY last_seen DESC",
            (uid,))
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Ban (is_plus = 0) ──
    if data.startswith("aban_"):
        uid = int(data[len("aban_"):])
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        if not u:
            await q.answer("Не найден", show_alert=True)
            return True

        new_val = 0 if u.get("is_plus") else 1
        await execute(pp, "UPDATE users SET is_plus = %s WHERE id = %s", (new_val, uid))
        await q.answer("Забанен (Plus снят)" if new_val == 0 else "Разбанен (Plus выдан)", show_alert=True)

        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        devs = await fetch_all(pp,
            "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = 0 ORDER BY last_seen DESC",
            (uid,))
        await q.edit_message_text(
            admin_user_text(u, devs),
            parse_mode="HTML",
            reply_markup=admin_user_kb(uid, bool(u.get("is_plus")), bool(u.get("no_device_limit"))),
        )
        return True

    # ── Payments ──
    if data.startswith("apayments_"):
        uid = int(data[len("apayments_"):])
        u = await fetch_one(pp, "SELECT * FROM users WHERE id = %s", (uid,))
        if not u:
            await q.answer("Не найден", show_alert=True)
            return True

        payments = await fetch_all(st,
            "SELECT p.*, a.title as app_title FROM purchases p "
            "JOIN apps a ON p.app_id = a.id "
            "WHERE p.zotus_username = %s ORDER BY p.created_at DESC LIMIT 10",
            (u["username"],))
        out = f"<b>💰 Платежи @{esc(u['username'])}</b>"
        if not payments:
            out += "\n\nНет платежей."
        else:
            for p in payments:
                status_icon = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(p.get("status"), "❓")
                out += f"\n\n{status_icon} {p.get('amount', 0):.0f} ₽ — {esc(p.get('app_title', ''))}"
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
            "Отправьте сообщение, которое будет разослано всем пользователям Plus с привязанным Telegram.\n\n"
            "/cancel для отмены.",
            parse_mode="HTML",
        )
        await q.answer()
        return True

    # ── Not handled by admin ──
    return False


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast message text."""
    if not context.user_data.pop("awaiting_broadcast", False):
        return

    tg_id = update.effective_user.id
    if tg_id not in ADMIN_IDS:
        return

    msg_text = update.message.text or update.message.caption or ""
    if not msg_text:
        return

    pp = zotuspp()
    targets = await fetch_all(pp,
        "SELECT chat_id, id FROM users WHERE is_plus = 1 AND chat_id IS NOT NULL AND chat_id > 0")
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
        await asyncio.sleep(0.05)  # ~20 msg/sec

    await update.message.reply_text(
        f"📢 Рассылка завершена.\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"
    )
