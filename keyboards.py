"""Inline keyboards for the bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_kb(is_plus: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📱 Устройства", callback_data="devices"),
        ],
        [InlineKeyboardButton("🔗 Подписка", callback_data="connect")],
    ]
    if is_plus:
        rows.append([InlineKeyboardButton("🔔 Уведомления", callback_data="notif")])
        rows.append([InlineKeyboardButton("🛒 WL устройства", callback_data="wl_buy")])
    if is_plus:
        rows.append([InlineKeyboardButton("⭐ Продлить Zotus++", callback_data="buy")])
    else:
        rows.append([InlineKeyboardButton("⭐ Купить Zotus++", callback_data="buy")])
    rows.append([InlineKeyboardButton("⚙️ Настройки", callback_data="settings")])
    if is_admin:
        rows.append([InlineKeyboardButton("👑 Админка", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def back_kb(data: str = "main", text: str = "🔙 Назад") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data)]])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="astats"),
         InlineKeyboardButton("👥 Пользователи", callback_data="ausers")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="abroadcast")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ])


def buy_tiers_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 100 ₽ / месяц", callback_data="buy_tier_monthly")],
        [InlineKeyboardButton("💳 249 ₽ / 3 месяца", callback_data="buy_tier_quarterly")],
        [InlineKeyboardButton("💳 479 ₽ / 6 месяцев", callback_data="buy_tier_halfyear")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ])


def payment_kb(payment_url: str, purchase_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"buy_check_{purchase_id}")],
    ])


def wl_buy_kb(wl_limit: int) -> InlineKeyboardMarkup:
    extra = max(0, wl_limit - 2)
    price = 67 if extra == 0 else 79
    label = f"💳 Купить слот — {price} ₽"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="wl_buy_confirm")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")],
    ])


def settings_kb(has_password: bool, has_plus: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_password:
        rows.append([InlineKeyboardButton("🔑 Сменить пароль", callback_data="chpass_start")])
    else:
        rows.append([InlineKeyboardButton("🔑 Установить пароль", callback_data="chpass_start")])
    if not has_plus:
        rows.append([InlineKeyboardButton("✈️ Привязать Telegram", callback_data="link_tg")])
    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    return InlineKeyboardMarkup(rows)


def devices_kb(devices: list[dict], prefix: str = "dev_del", restore: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for i, d in enumerate(devices, 1):
        name = (d.get("device_model") or d.get("device_os") or "Устройство")[:25]
        cb = f"{prefix}_{d['device_id']}"
        icon = "♻" if restore else "🗑"
        rows.append([InlineKeyboardButton(f"{icon} {i}. {name}", callback_data=cb)])
    return InlineKeyboardMarkup(rows)


def admin_user_kb(user_id: int, is_plus: bool, no_limit: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔽 Снять Plus" if is_plus else "⭐ Выдать Plus",
                callback_data=f"atoggle_plus_{user_id}",
            ),
            InlineKeyboardButton(
                "🔒 Лимит" if no_limit else "♾ Безлимит",
                callback_data=f"atoggle_limit_{user_id}",
            ),
        ],
        [InlineKeyboardButton("🛡 Бан" if is_plus else "🔓 Разбан", callback_data=f"aban_{user_id}")],
        [InlineKeyboardButton("💰 Платежи", callback_data=f"apayments_{user_id}")],
        [InlineKeyboardButton("🔙 К списку", callback_data="ausers")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="cancel_state")]])
