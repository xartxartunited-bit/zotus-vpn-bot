"""Background tasks: subscription expiry notifications, payment polling."""
import asyncio
import logging
from datetime import datetime, timedelta

import db

logger = logging.getLogger(__name__)


async def notify_expiring_subscriptions(bot) -> None:
    """Send notifications for subscriptions expiring in configured days."""
    from config import NOTIFY_DAYS

    today = datetime.now().date()

    for days in NOTIFY_DAYS:
        target_date = today + timedelta(days=days)

        users = await db.get_expiring_users(days)

        for u in users:
            try:
                exp_str = str(u.get("subscription_expires", ""))
                if not exp_str or len(exp_str) < 10:
                    continue
                exp_date = datetime.strptime(exp_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

            if exp_date != target_date:
                continue

            chat_id = u.get("chat_id")
            if not chat_id:
                continue

            if days == 0:
                msg = ("⚠️ <b>Подписка Zotus++ истекает сегодня!</b>\n\n"
                       "Продлите сейчас чтобы не потерять доступ.\n"
                       "/buy — купить Zotus++")
            else:
                msg = (f"📅 <b>Подписка Zotus++ истекает через {days} дн.</b>\n\n"
                       "Не забудьте продлить.\n"
                       "/buy — продлить Zotus++")

            try:
                await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode="HTML")
                logger.info(f"Expiry notification sent to user {u['id']} ({u['username']})")
            except Exception as e:
                logger.warning(f"Failed to notify user {u['id']}: {e}")

            await asyncio.sleep(0.05)


async def poll_pending_payments(bot) -> None:
    """Check pending payments and notify users when completed."""
    from yookassa import _call

    pending = await db.get_pending_payments()

    for p in pending:
        try:
            result = await _call("check_payment", {"purchase_id": p["id"]})
            if not result or not result.get("success"):
                continue

            status = result.get("status")
            if status == "completed":
                user = await db.find_user_by_username(p.get("zotus_username", ""))
                if user and user.get("chat_id"):
                    try:
                        await bot.send_message(
                            chat_id=int(user["chat_id"]),
                            text=f"✅ Оплата {p['amount']:.0f} ₽ прошла!\n\n/start",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        except Exception:
            continue

        await asyncio.sleep(0.1)
