"""Zotus++ Telegram Bot — Configuration"""

# Bot
BOT_TOKEN = "8790938688:AAHtNliw_QQ_xEayR_xguegCwm3d1fW9C7s"
ADMIN_IDS = [6971992145]

# Webhook
WEBHOOK_HOST = "zotus.bothost.tech"
WEBHOOK_PORT = 3000
WEBHOOK_PATH = "/webhook"

# DB — Zotus++ (vpn.zotus.ru/plus)
# ⚠️ На внешнем хостинге заменить localhost на IP или хостнейм сервера БД
ZOTUSPP_DB = {
    "host": "localhost",
    "port": 3306,
    "user": "u3080254_zotuspp",
    "password": "8CocaCola8!_",
    "db": "u3080254_zotuspp",
    "charset": "utf8mb4",
}

# DB — Store (store.zotus.ru)
STORE_DB = {
    "host": "localhost",
    "port": 3306,
    "user": "u3080254_store",
    "password": "8CocaCola8!_",
    "db": "u3080254_store",
    "charset": "utf8mb4",
}

# YooKassa (Store settings)
STORE_URL = "https://store.zotus.ru"
ZOTUSPP_STORE_APP_SLUG = "zotus-plus"
YOOKASSA_RETURN_URL = "https://store.zotus.ru/yookassa/success.php"

# VPN URLs
VPN_DOMAIN = "vpn.zotus.ru"
AVATAR_UPLOAD_URL = f"https://{VPN_DOMAIN}/plus/api/upload_avatar.php"
AVATAR_UPLOAD_KEY = "твой_пароль"

# Device limits
MAX_BASE_DEVICES = 3
MAX_WL_DEVICES = 7  # 2 base + 5 extra

# Prices
PLUS_PRICES = {
    "monthly": 100,
    "quarterly": 249,
    "halfyear": 479,
}
WL_EXTRA_FIRST = 67
WL_EXTRA_NEXT = 79

# Subscription expiry notifications (days before)
NOTIFY_DAYS = [3, 0]

# Polling intervals (seconds)
PAYMENT_POLL_INTERVAL = 60
NOTIFY_CHECK_INTERVAL = 3600  # 1 hour
