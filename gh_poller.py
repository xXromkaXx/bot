import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

CONTROL_CHAT_ID = int(os.environ["CONTROL_CHAT_ID"])
DEFAULT_TARGET_CHAT_ID = int(os.environ.get("DAILY_CHAT_ID", "986095695"))
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Kyiv")

STATE_PATH = Path(os.environ.get("STATE_FILE", "control_state.json"))


def now_tz() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def default_state() -> dict:
    return {
        "sending_enabled": True,
        "daily_enabled": True,
        "daily_chat_id": DEFAULT_TARGET_CHAT_ID,
        "daily_hour": 4,
        "daily_minute": 0,
        "scheduled": [],
        "next_id": 1,
        "last_command_id": 0,
        "last_daily_date": "",
    }


def load_state() -> dict:
    if not STATE_PATH.exists():
        return default_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        base = default_state()
        base.update(data)
        return base
    except Exception:
        return default_state()


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_hhmm(value: str):
    hh, mm = value.split(":")
    h = int(hh)
    m = int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError
    return h, m


def format_queue(rows: List[dict]) -> str:
    if not rows:
        return "Черга порожня."
    lines = []
    for row in rows:
        lines.append(f"#{row['id']} | {row['send_at']} | chat {row['chat_id']} | {row['text']}")
    return "\n".join(lines)


async def run() -> None:
    state = load_state()
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Session is not authorized. Regenerate SESSION_STRING.")

    now = now_tz()
    changed = False

    async def reply(text: str) -> None:
        await client.send_message(CONTROL_CHAT_ID, text)

    async def send_if_enabled(chat_id: int, text: str) -> bool:
        if not state["sending_enabled"]:
            return False
        await client.send_message(chat_id, text)
        return True

    # 1) Process new commands from control chat (your own outgoing messages)
    msgs = await client.get_messages(CONTROL_CHAT_ID, limit=100)
    commands = []
    for m in msgs:
        if not m or not m.out or not m.message:
            continue
        if m.id <= int(state["last_command_id"]):
            continue
        text = m.message.strip()
        if text.startswith("/"):
            commands.append(m)

    commands.sort(key=lambda x: x.id)
    for m in commands:
        text = m.message.strip()
        handled = True

        if text == "/help":
            await reply(
                "/sending on|off|status\n"
                "/daily on|off|status\n"
                "/dailytime HH:MM\n"
                "/dailychat <chat_id>\n"
                "/sendin <minutes> <text>\n"
                "/queue\n"
                "/cancel <id>\n"
                "/sendnow <text>\n"
                "/state"
            )
        elif text.startswith("/sending "):
            arg = text.split(maxsplit=1)[1].lower()
            if arg == "on":
                state["sending_enabled"] = True
                await reply("✅ Sending ON")
                changed = True
            elif arg == "off":
                state["sending_enabled"] = False
                await reply("🛑 Sending OFF")
                changed = True
            elif arg == "status":
                await reply(f"Sending: {'ON' if state['sending_enabled'] else 'OFF'}")
            else:
                await reply("Формат: /sending on|off|status")
        elif text.startswith("/daily "):
            arg = text.split(maxsplit=1)[1].lower()
            if arg == "on":
                state["daily_enabled"] = True
                await reply("✅ Daily ON")
                changed = True
            elif arg == "off":
                state["daily_enabled"] = False
                await reply("🛑 Daily OFF")
                changed = True
            elif arg == "status":
                await reply(
                    f"Daily: {'ON' if state['daily_enabled'] else 'OFF'} | "
                    f"{state['daily_hour']:02d}:{state['daily_minute']:02d} | chat {state['daily_chat_id']}"
                )
            else:
                await reply("Формат: /daily on|off|status")
        elif text.startswith("/dailytime "):
            try:
                h, mm = parse_hhmm(text.split(maxsplit=1)[1].strip())
                state["daily_hour"] = h
                state["daily_minute"] = mm
                changed = True
                await reply(f"✅ Daily time: {h:02d}:{mm:02d}")
            except Exception:
                await reply("Формат: /dailytime HH:MM")
        elif text.startswith("/dailychat "):
            try:
                cid = int(text.split(maxsplit=1)[1].strip())
                state["daily_chat_id"] = cid
                changed = True
                await reply(f"✅ Daily chat: {cid}")
            except Exception:
                await reply("Формат: /dailychat <chat_id>")
        elif text.startswith("/sendin "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await reply("Формат: /sendin <minutes> <text>")
            else:
                try:
                    mins = int(parts[1])
                    if mins < 0:
                        raise ValueError
                    send_at = now_tz() + timedelta(minutes=mins)
                    item = {
                        "id": int(state["next_id"]),
                        "chat_id": int(state["daily_chat_id"]),
                        "text": parts[2],
                        "send_at": send_at.isoformat(),
                    }
                    state["next_id"] = int(state["next_id"]) + 1
                    state["scheduled"].append(item)
                    changed = True
                    await reply(f"✅ Заплановано #{item['id']} на {send_at.strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception:
                    await reply("minutes має бути числом >= 0")
        elif text == "/queue":
            await reply(format_queue(state["scheduled"]))
        elif text.startswith("/cancel "):
            try:
                sid = int(text.split(maxsplit=1)[1].strip())
                before = len(state["scheduled"])
                state["scheduled"] = [x for x in state["scheduled"] if x["id"] != sid]
                if len(state["scheduled"]) < before:
                    await reply(f"✅ Скасовано #{sid}")
                    changed = True
                else:
                    await reply("Немає такого id")
            except Exception:
                await reply("Формат: /cancel <id>")
        elif text.startswith("/sendnow "):
            msg = text.split(maxsplit=1)[1]
            ok = await send_if_enabled(int(state["daily_chat_id"]), msg)
            await reply("✅ Відправлено зараз." if ok else "🛑 Не відправлено: sending=OFF")
        elif text == "/state":
            await reply(
                f"sending={'ON' if state['sending_enabled'] else 'OFF'}\n"
                f"daily={'ON' if state['daily_enabled'] else 'OFF'}\n"
                f"time={state['daily_hour']:02d}:{state['daily_minute']:02d}\n"
                f"daily_chat={state['daily_chat_id']}\n"
                f"queue={len(state['scheduled'])}"
            )
        else:
            handled = False

        if handled:
            state["last_command_id"] = max(int(state["last_command_id"]), int(m.id))
            changed = True

    # 2) Execute due scheduled messages
    due = []
    keep = []
    for row in state["scheduled"]:
        try:
            send_at = datetime.fromisoformat(row["send_at"])
        except Exception:
            continue
        if send_at <= now_tz():
            due.append(row)
        else:
            keep.append(row)

    for row in due:
        ok = await send_if_enabled(int(row["chat_id"]), row["text"])
        mark = "✅" if ok else "🛑"
        await reply(f"{mark} Scheduled #{row['id']} {'sent' if ok else 'skipped'}")
        changed = True
    if due:
        state["scheduled"] = keep

    # 3) Daily message once per local date
    today = now_tz().date().isoformat()
    if state["daily_enabled"] and state["sending_enabled"]:
        at_or_after = (
            now.hour > int(state["daily_hour"]) or
            (now.hour == int(state["daily_hour"]) and now.minute >= int(state["daily_minute"]))
        )
        if at_or_after and state.get("last_daily_date", "") != today:
            await client.send_message(int(state["daily_chat_id"]), "вогник")
            state["last_daily_date"] = today
            changed = True
            await reply("✅ Daily 'вогник' sent")

    if changed:
        save_state(state)
        print("State updated", flush=True)
    else:
        print("No changes", flush=True)

    await client.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
