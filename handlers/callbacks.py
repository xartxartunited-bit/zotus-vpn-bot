"""Inline callback handlers: status, devices, subscriptions, buy, WL."""
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import zotuspp, store, fetch_one, execute, fetch_all, fetch_val
from keyboards import (
    main_kb, back_kb, devices_kb, buy_tiers_kb, payment_kb, wl_buy_kb,
    cancel_kb,
)
from utils import profile_text, device_text, notification_text
from config import (
    ADMIN_IDS, MAX_WL_DEVICES, PLUS_PRICES, WL_EXTRA_FIRST, WL_EXTRA_NEXT,
    ZOTUSPP_STORE_APP_SLUG,
)
from yookassa import create_payment, check_payment, get_wl_usernames


async def _get_user(tg_id: int) -> dict | None:
    return await fetch_one(zotuspp(), "SELECT * FROM users WHERE telegram_id = %s", (tg_id,))


async def _get_store_user_id(username: str) -> int | None:
    return await fetch_val(store(), "SELECT id FROM users WHERE username = %s", (username,))


async def _profile_text(user: dict) -> str:
    pp = zotuspp()
    uid = user["id"]
    plus_count = await fetch_val(pp,
        "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0 AND sub_type = 'plus'",
        (uid,)) or 0
    wl_count = await fetch_val(pp,
        "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0 AND sub_type = 'wl'",
        (uid,)) or 0
    wl_limit = int(user.get("wl_device_limit", 2) or 2)
    streak = await fetch_one(pp,
        "SELECT current_streak, max_streak FROM user_streaks WHERE user_id = %s",
        (uid,)) or {"current_streak": 0, "max_streak": 0}
    bal = await fetch_val(store(), "SELECT balance FROM users WHERE username = %s", (user["username"],))
    return profile_text(user, plus_count, wl_count, wl_limit, bal, streak)


# ─── Main router ────────────────────────────────────────────────────────

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data
    tg_id = q.from_user.id
    chat_id = q.message.chat.id
    mid = q.message.message_id
    is_admin = tg_id in ADMIN_IDS

    user = await _get_user(tg_id)
    if user:
        from handlers.activity import track_activity
        await track_activity(user["id"])

    pp = zotuspp()

    # ── Navigation ──
    if data == "main":
        user = await _get_user(tg_id)
        if not user:
            await q.edit_message_text("Аккаунт не привязан. /start", parse_mode="HTML")
            return
        await q.edit_message_text(
            await _profile_text(user),
            parse_mode="HTML",
            reply_markup=main_kb(bool(user.get("is_plus")), is_admin),
        )
        return

    if data == "status":
        user = await _get_user(tg_id)
        if not user:
            await q.edit_message_text("Аккаунт не привязан. /start", parse_mode="HTML")
            return
        await q.edit_message_text(
            await _profile_text(user),
            parse_mode="HTML",
            reply_markup=main_kb(bool(user.get("is_plus")), is_admin),
        )
        return

    # ── Devices ──
    if data == "devices":
        user = await _get_user(tg_id)
        if not user:
            await q.answer("Аккаунт не привязан.", show_alert=True)
            return
        await _show_devices(q, user, is_admin, False)
        return

    if data == "devices_del":
        user = await _get_user(tg_id)
        if not user:
            await q.answer("Аккаунт не привязан.", show_alert=True)
            return
        await _show_devices(q, user, is_admin, True)
        return

    if data.startswith("dev_del_"):
        dev_id = data[len("dev_del_"):]
        user = await _get_user(tg_id)
        if not user:
            return
        await execute(pp,
            "UPDATE sub_devices SET is_deleted = 1 WHERE user_id = %s AND device_id = %s",
            (user["id"], dev_id))
        await q.answer("Удалено")
        await _show_devices(q, user, is_admin, False)
        return

    if data.startswith("dev_restore_"):
        dev_id = data[len("dev_restore_"):]
        user = await _get_user(tg_id)
        if not user:
            return
        uid = user["id"]
        is_unl = bool(user.get("no_device_limit"))
        cnt = await fetch_val(pp,
            "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0 AND sub_type != 'wl'",
            (uid,)) or 0
        if not is_unl and cnt >= 3:
            await q.answer("Нет свободных слотов (3/3)", show_alert=True)
            return
        await execute(pp,
            "UPDATE sub_devices SET is_deleted = 0 WHERE user_id = %s AND device_id = %s",
            (uid, dev_id))
        await q.answer("Восстановлено")
        await _show_devices(q, user, is_admin, True)
        return

    # ── Subscribe ──
    if data == "connect":
        user = await _get_user(tg_id)
        if not user or not user.get("is_plus") or not user.get("sub_token"):
            await q.edit_message_text(
                "⭐ Требуется Zotus++.\n\nКупить: https://store.zotus.ru/app/zotus-plus",
                parse_mode="HTML",
                reply_markup=main_kb(False, is_admin),
            )
            return
        sub_url = f"https://vpn.zotus.ru/plus/sub/{user['sub_token']}"
        wl_url = f"https://vpn.zotus.ru/plus/sub/wl/{user['sub_token']}"
        text = (
            f"<b>🔗 Подписка Zotus++</b>\n\n"
            f"<code>{sub_url}</code>\n\n"
            f"<b>🗂 WhiteList подписка</b>\n"
            f"<code>{wl_url}</code>\n\n"
            f"Скопируйте ссылку и вставьте в VPN-клиент."
        )
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=back_kb())
        return

    # ── Notifications ──
    if data == "notif":
        user = await _get_user(tg_id)
        if not user or not user.get("is_plus"):
            await q.answer("Только для Zotus++", show_alert=True)
            return
        notifs = await _fetch_notifications()
        await q.edit_message_text(
            notification_text(notifs),
            parse_mode="HTML",
            reply_markup=back_kb(),
        )
        return

    # ── Buy ──
    if data == "buy":
        user = await _get_user(tg_id)
        out = (
            "<b>⭐ Zotus++</b>\n\n"
            f"• {PLUS_PRICES['monthly']} ₽ / месяц\n"
            f"• {PLUS_PRICES['quarterly']} ₽ / 3 месяца\n"
            f"• {PLUS_PRICES['halfyear']} ₽ / 6 месяцев\n\n"
            "❄️ Цена не меняется со временем\n\n"
            "Выберите тариф:"
        )
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=buy_tiers_kb())
        return

    if data.startswith("buy_tier_"):
        tier = data[len("buy_tier_"):]
        user = await _get_user(tg_id)
        if not user:
            await q.answer("Аккаунт не привязан.", show_alert=True)
            return
        suid = await _get_store_user_id(user["username"])
        if not suid:
            await q.answer("Store-аккаунт не найден. /start", show_alert=True)
            return

        amount = PLUS_PRICES.get(tier, 100)
        result = await create_payment(
            float(amount), user["username"], tier, suid,
            wl_extra=False,
        )
        if not result:
            await q.answer("Ошибка создания платежа. Попробуйте позже.", show_alert=True)
            return

        await q.edit_message_text(
            f"💳 <b>Оплата {amount} ₽</b>\n\n"
            f"Тариф: {tier}\n"
            f"Аккаунт: <code>{user['username']}</code>\n\n"
            f"Нажмите «Оплатить» и завершите платёж.\n"
            f"Затем нажмите «Проверить оплату».",
            parse_mode="HTML",
            reply_markup=payment_kb(result["payment_url"], result["purchase_id"]),
        )
        return

    if data.startswith("buy_check_"):
        pid = int(data[len("buy_check_"):])
        result = await check_payment(pid)
        if not result:
            await q.answer("Ошибка проверки", show_alert=True)
            return

        status = result["status"]
        if status == "completed":
            user = await _get_user(tg_id)
            await q.edit_message_text(
                "✅ <b>Оплата прошла!</b>\n\nПодписка активирована.\n/start для обновления статуса.",
                parse_mode="HTML",
                reply_markup=main_kb(True, is_admin),
            )
        elif status == "failed":
            await q.edit_message_text(
                "❌ Платёж не прошёл. Попробуйте снова.",
                parse_mode="HTML",
                reply_markup=buy_tiers_kb(),
            )
        else:
            await q.answer("Платёж ещё обрабатывается. Проверьте через минуту.", show_alert=True)
        return

    # ── WL Buy ──
    if data == "wl_buy":
        user = await _get_user(tg_id)
        if not user or not user.get("is_plus"):
            await q.answer("Только для Zotus++", show_alert=True)
            return
        wl_limit = int(user.get("wl_device_limit", 2) or 2)
        if wl_limit >= MAX_WL_DEVICES:
            await q.answer(f"Достигнут лимит ({MAX_WL_DEVICES} устройств)", show_alert=True)
            return
        extra_count = max(0, wl_limit - 2)
        price = WL_EXTRA_FIRST if extra_count == 0 else WL_EXTRA_NEXT
        await q.edit_message_text(
            f"<b>🛒 WL — доп. устройство</b>\n\n"
            f"Текущий лимит: {wl_limit}\n"
            f"Доп. слотов куплено: {extra_count}\n"
            f"Цена: <b>{price} ₽</b>\n\n"
            f"Первое доп. устройство — {WL_EXTRA_FIRST}₽, остальные — {WL_EXTRA_NEXT}₽.\n"
            f"Максимум: {MAX_WL_DEVICES} устройств.",
            parse_mode="HTML",
            reply_markup=wl_buy_kb(wl_limit),
        )
        return

    if data == "wl_buy_confirm":
        user = await _get_user(tg_id)
        if not user:
            await q.answer("Аккаунт не привязан.", show_alert=True)
            return
        wl_limit = int(user.get("wl_device_limit", 2) or 2)
        if wl_limit >= MAX_WL_DEVICES:
            await q.answer("Лимит достигнут", show_alert=True)
            return
        extra_count = max(0, wl_limit - 2)
        price = WL_EXTRA_FIRST if extra_count == 0 else WL_EXTRA_NEXT
        suid = await _get_store_user_id(user["username"])
        if not suid:
            await q.answer("Store-аккаунт не найден.", show_alert=True)
            return

        result = await create_payment(
            float(price), user["username"], "wl_extra", suid,
            wl_extra=True,
        )
        if not result:
            await q.answer("Ошибка создания платежа", show_alert=True)
            return

        await q.edit_message_text(
            f"💳 <b>WL слот — {price} ₽</b>\n\n"
            f"Аккаунт: <code>{user['username']}</code>\n\n"
            f"Оплатите и нажмите «Проверить».",
            parse_mode="HTML",
            reply_markup=payment_kb(result["payment_url"], result["purchase_id"]),
        )
        return

    # ── Settings navigation ──
    if data == "settings":
        user = await _get_user(tg_id)
        if not user:
            await q.answer("Аккаунт не привязан.", show_alert=True)
            return
        from keyboards import settings_kb
        has_pw = bool(user.get("password") and user["password"] is not None)
        has_plus = bool(user.get("is_plus"))
        await q.edit_message_text(
            "<b>⚙️ Настройки</b>\n\nЧто меняем?",
            parse_mode="HTML",
            reply_markup=settings_kb(has_pw, has_plus),
        )
        return

    # ── Fallback ──
    await q.answer(f"Неизвестное действие: {data}")


# ─── Helpers ────────────────────────────────────────────────────────────

async def _show_devices(q, user: dict, is_admin: bool, deleted: bool) -> None:
    pp = zotuspp()
    uid = user["id"]
    is_unl = bool(user.get("no_device_limit"))
    flt = 1 if deleted else 0
    devs = await fetch_all(pp,
        "SELECT * FROM sub_devices WHERE user_id = %s AND is_deleted = %s ORDER BY last_seen DESC",
        (uid, flt))
    act_cnt = await fetch_val(pp,
        "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 0", (uid,)) or 0

    if deleted:
        out = f"<b>📂 Удалённые устройства</b>"
    else:
        out = f"<b>📱 Устройства ({len(devs)}" + ("♾" if is_unl else "/3") + ")</b>"

    if not devs:
        out += "\n\nНет устройств."
        kb = back_kb("devices" if deleted else "main")
    else:
        for i, d in enumerate(devs, 1):
            out += f"\n\n{device_text(d, i, show_type=True)}"

        prefix = "dev_restore" if deleted else "dev_del"
        dkb = devices_kb(devs, prefix=prefix, restore=deleted)

        rows = list(dkb.inline_keyboard)
        if not deleted:
            dels = await fetch_val(pp,
                "SELECT COUNT(*) FROM sub_devices WHERE user_id = %s AND is_deleted = 1",
                (uid,)) or 0
            if dels > 0:
                rows.append([InlineKeyboardButton(
                    f"📂 Удалённые ({dels})", callback_data="devices_del")])
        rows.append([InlineKeyboardButton(
            "🔙 Назад", callback_data="devices" if deleted else "main")])
        kb = InlineKeyboardMarkup(rows)

    try:
        await q.edit_message_text(out, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass


async def _fetch_notifications() -> list[dict]:
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                "https://vpn.zotus.ru/plus/notifications.json", timeout=10
            ) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None) or []
    except Exception:
        pass
    return []
