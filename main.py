"""Zotus++ Telegram Bot — Main entry point.

Webhook mode for ctrlfree.host.
Background tasks via JobQueue.
"""
import asyncio
import logging
import sys

from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder,
    CommandHandler, CallbackQueryHandler, MessageHandler, filters,
    PicklePersistence,
)

from config import (
    BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_PATH,
    ADMIN_IDS, NOTIFY_CHECK_INTERVAL, PAYMENT_POLL_INTERVAL,
)
from db import init_pools, close_pools
from handlers.start import start
from handlers.callbacks import callback_router
from handlers.commands import status_cmd, devices_cmd, buy_cmd, link_cmd, cancel_cmd
from handlers.settings import password_conv_handler
from admin import admin_router, handle_broadcast_message
from tasks import notify_expiring_subscriptions, poll_pending_payments

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def combined_callback(update: Update, context) -> None:
    """Route callbacks: skip conversation ones, try admin, then user."""
    q = update.callback_query
    if not q:
        return

    # Skip callbacks handled by ConversationHandler
    if q.data in ("chpass_start", "cancel_state"):
        return

    # Try admin router first
    handled = await admin_router(update, context)
    if handled:
        return

    # Fall through to user callbacks
    await callback_router(update, context)


async def broadcast_handler(update: Update, context) -> None:
    """Handle broadcast messages from admin."""
    await handle_broadcast_message(update, context)


async def post_init(app: Application) -> None:
    """Called after application is initialized."""
    logger.info("Initializing database pools...")
    await init_pools()
    logger.info("Database pools ready.")

    # Schedule background tasks
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            notify_expiring_subscriptions,
            interval=NOTIFY_CHECK_INTERVAL,
            first=10,
            name="notify_expiry",
            data=app.bot,
        )
        job_queue.run_repeating(
            poll_pending_payments,
            interval=PAYMENT_POLL_INTERVAL,
            first=30,
            name="poll_payments",
            data=app.bot,
        )
        logger.info("Background tasks scheduled.")


async def post_shutdown(app: Application) -> None:
    """Called on shutdown."""
    logger.info("Closing database pools...")
    await close_pools()
    logger.info("Shutdown complete.")


def main() -> None:
    # Build application with job queue for background tasks
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Conversation handlers ──
    app.add_handler(password_conv_handler())

    # ── Command handlers ──
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("devices", devices_cmd))
    app.add_handler(CommandHandler("buy", buy_cmd))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))

    # ── Callback handler (all inline buttons) ──
    app.add_handler(CallbackQueryHandler(combined_callback))

    # ── Broadcast message handler (admin text for mass send) ──
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_IDS),
        broadcast_handler,
    ))

    # ── Start ──
    logger.info(f"Starting bot in webhook mode on {WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_PATH}")
    app.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}",
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
