"""Helper functions for formatting profile, device, notification texts."""
from config import MAX_BASE_DEVICES, MAX_WL_DEVICES


def profile_text(user: dict, plus_count: int, wl_count: int, wl_limit: int,
                 balance: float | None, streak: dict) -> str:
    uname = user.get("username", "—")
    is_plus = bool(user.get("is_plus"))
    is_unlimited = bool(user.get("no_device_limit"))

    out = f"👤 <b>{esc(uname)}</b>"

    if is_plus:
        out += "\n⭐ <b>Zotus++ активен</b>"
        pid = user.get("plus_id")
        if pid:
            out += f"\nID: <code>{esc(pid)}</code>"
        expires = user.get("subscription_expires")
        if expires and str(expires) not in ("0000-00-00 00:00:00", "None", ""):
            out += f"\n📅 До: {_fmt_date(expires)}"
    else:
        out += "\n🆓 <b>Бесплатный</b>"

    created = user.get("created_at")
    if created and str(created) not in ("0000-00-00 00:00:00", "None", ""):
        out += f"\n📅 Зареган: {_fmt_date(created)}"

    device_label = f"{plus_count}" + (" ♾" if is_unlimited else f" / {MAX_BASE_DEVICES}")
    out += f"\n📱 Plus устройств: {device_label}"

    if is_plus and wl_limit > 0:
        out += f"\n🗂 WL устройств: {wl_count} / {wl_limit}"

    if is_unlimited:
        out += "\n♾ Безлимит устройств"

    if balance is not None and balance > 0:
        out += f"\n💰 Баланс: {balance:.0f} ₽"

    if streak.get("current_streak", 0) > 0:
        out += f"\n🔥 Серия: {streak['current_streak']} дн. (макс: {streak.get('max_streak', 0)})"

    tg = user.get("telegram")
    if tg:
        out += f"\n✈️ @{esc(tg)}"
    return out


def device_text(d: dict, idx: int, show_type: bool = False) -> str:
    name = d.get("device_name") or d.get("device_model") or d.get("device_os") or "Неизвестно"
    os_name = d.get("device_os", "—")
    ver = d.get("app_version", "")
    seen = d.get("last_seen")
    seen_str = _fmt_date(seen) if seen else "—"
    out = f"{idx}. <b>{esc(name)}</b>"
    if ver:
        out += f" v{esc(ver)}"
    out += f"\n   └ {esc(os_name)} · {seen_str}"
    if show_type:
        st = d.get("sub_type", "plus")
        out += f" · {st.upper()}"
    return out


def notification_text(notifications: list[dict]) -> str:
    if not notifications:
        return "🔔 <b>Уведомления</b>\n\nПока нет уведомлений."
    out = "🔔 <b>Уведомления</b>"
    for n in notifications[:5]:
        out += f"\n\n<b>{esc(n.get('title', ''))}</b>"
        out += f"\n{esc(n.get('message', ''))}"
        d = n.get("date", "")
        if d:
            out += f"\n<small>{esc(d)}</small>"
    return out


def admin_user_text(u: dict, devices: list[dict]) -> str:
    out = f"👤 <b>{esc(u.get('username', '—'))}</b>"
    out += f"\nID: {u['id']}"
    out += f"\nPlus: {'⭐ Да' if u.get('is_plus') else '🆓 Нет'}"
    if u.get("plus_id"):
        out += f"\nPlus ID: <code>{esc(u['plus_id'])}</code>"
    expires = u.get("subscription_expires")
    if expires and str(expires) not in ("0000-00-00 00:00:00", "None", ""):
        out += f"\nИстекает: {_fmt_date(expires)}"
    out += f"\nЛимит устр: {'♾ Безлимит' if u.get('no_device_limit') else '3'}"
    wl = u.get("wl_device_limit", 2)
    out += f"\nWL лимит: {wl}"
    tg = u.get("telegram")
    if tg:
        out += f"\nTelegram: @{esc(tg)}"
    out += f"\nАктивных устр: {len(devices)}"
    if u.get("sub_token"):
        out += f"\nТокен: <code>{esc(str(u['sub_token'])[:16])}...</code>"
    return out


def esc(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_date(val) -> str:
    s = str(val)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            from datetime import datetime
            dt = datetime.strptime(s[:19], fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return s[:10]
