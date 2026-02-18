import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List
from zoneinfo import ZoneInfo

from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

CONTROL_CHAT_ID = int(os.environ.get("CONTROL_CHAT_ID", "8318118201"))
DEFAULT_TARGET_CHAT_ID = int(os.environ.get("DAILY_CHAT_ID", "986095695"))
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Kyiv")

STATE_FILE = os.environ.get("STATE_FILE", "control_state.json")


@dataclass
class ScheduledItem:
    id: int
    chat_id: int
    text: str
    send_at: str  # ISO datetime


client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
state = {
    "sending_enabled": True,
    "daily_enabled": True,
    "daily_chat_id": DEFAULT_TARGET_CHAT_ID,
    "daily_hour": 4,
    "daily_minute": 0,
    "scheduled": [],
    "next_id": 1,
}
scheduled_tasks: Dict[int, asyncio.Task] = {}


def load_state() -> None:
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        state.update(saved)
    except Exception:
        pass


def save_state() -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def next_daily_run(tz: ZoneInfo) -> datetime:
    now = datetime.now(tz)
    run_at = now.replace(
        hour=int(state["daily_hour"]),
        minute=int(state["daily_minute"]),
        second=0,
        microsecond=0,
    )
    if run_at <= now:
        run_at += timedelta(days=1)
    return run_at


def fmt_queue(rows: List[dict]) -> str:
    if not rows:
        return "Черга порожня."
    lines = []
    for row in rows:
        lines.append(
            f"#{row['id']} -> chat {row['chat_id']} | {row['send_at']} | {row['text']}"
        )
    return "\n".join(lines)


async def send_if_enabled(chat_id: int, text: str) -> bool:
    if not state["sending_enabled"]:
        return False
    await client.send_message(chat_id, text)
    return True


async def run_scheduled(item: dict) -> None:
    try:
        send_at = parse_iso(item["send_at"])
        now = datetime.now(ZoneInfo(TIMEZONE))
        delay = (send_at - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        ok = await send_if_enabled(item["chat_id"], item["text"])
        if ok:
            print(f"Scheduled sent: #{item['id']}", flush=True)
        else:
            print(f"Scheduled skipped (sending disabled): #{item['id']}", flush=True)
    except asyncio.CancelledError:
        return
    finally:
        state["scheduled"] = [x for x in state["scheduled"] if x["id"] != item["id"]]
        save_state()
        scheduled_tasks.pop(item["id"], None)


def schedule_item(item: dict) -> None:
    task = asyncio.create_task(run_scheduled(item))
    scheduled_tasks[item["id"]] = task


async def daily_loop() -> None:
    tz = ZoneInfo(TIMEZONE)
    while True:
        run_at = next_daily_run(tz)
        wait_seconds = (run_at - datetime.now(tz)).total_seconds()
        await asyncio.sleep(max(wait_seconds, 0))

        if not state["daily_enabled"]:
            continue

        ok = await send_if_enabled(int(state["daily_chat_id"]), "вогник")
        mark = "sent" if ok else "skipped (sending disabled)"
        print(f"Daily message {mark} at {datetime.now(tz)}", flush=True)


@client.on(events.NewMessage(outgoing=True))
async def commands(event) -> None:
    text = (event.raw_text or "").strip()
    if not text.startswith("/"):
        return
    if event.chat_id != CONTROL_CHAT_ID:
        return

    if text == "/help":
        await event.reply(
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
        return

    if text.startswith("/sending "):
        arg = text.split(maxsplit=1)[1].strip().lower()
        if arg == "on":
            state["sending_enabled"] = True
            save_state()
            await event.reply("✅ Відправка увімкнена.")
        elif arg == "off":
            state["sending_enabled"] = False
            save_state()
            await event.reply("🛑 Відправка вимкнена.")
        elif arg == "status":
            val = "ON" if state["sending_enabled"] else "OFF"
            await event.reply(f"Sending: {val}")
        else:
            await event.reply("Формат: /sending on|off|status")
        return

    if text.startswith("/daily "):
        arg = text.split(maxsplit=1)[1].strip().lower()
        if arg == "on":
            state["daily_enabled"] = True
            save_state()
            await event.reply("✅ Щоденна відправка о 04:00 увімкнена.")
        elif arg == "off":
            state["daily_enabled"] = False
            save_state()
            await event.reply("🛑 Щоденна відправка вимкнена.")
        elif arg == "status":
            val = "ON" if state["daily_enabled"] else "OFF"
            await event.reply(
                f"Daily: {val} | time {state['daily_hour']:02d}:{state['daily_minute']:02d} "
                f"| chat {state['daily_chat_id']}"
            )
        else:
            await event.reply("Формат: /daily on|off|status")
        return

    if text.startswith("/dailytime "):
        arg = text.split(maxsplit=1)[1].strip()
        try:
            hh, mm = arg.split(":")
            hh_i = int(hh)
            mm_i = int(mm)
            if not (0 <= hh_i <= 23 and 0 <= mm_i <= 59):
                raise ValueError
        except Exception:
            await event.reply("Формат: /dailytime HH:MM")
            return
        state["daily_hour"] = hh_i
        state["daily_minute"] = mm_i
        save_state()
        await event.reply(f"✅ Новий час: {hh_i:02d}:{mm_i:02d}")
        return

    if text.startswith("/dailychat "):
        arg = text.split(maxsplit=1)[1].strip()
        try:
            cid = int(arg)
        except ValueError:
            await event.reply("Формат: /dailychat <chat_id>")
            return
        state["daily_chat_id"] = cid
        save_state()
        await event.reply(f"✅ Daily chat: {cid}")
        return

    if text.startswith("/sendin "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await event.reply("Формат: /sendin <minutes> <text>")
            return
        try:
            mins = int(parts[1])
            if mins < 0:
                raise ValueError
        except ValueError:
            await event.reply("minutes має бути числом >= 0")
            return
        msg = parts[2]
        send_at = datetime.now(ZoneInfo(TIMEZONE)) + timedelta(minutes=mins)
        item = {
            "id": int(state["next_id"]),
            "chat_id": int(state["daily_chat_id"]),
            "text": msg,
            "send_at": send_at.isoformat(),
        }
        state["next_id"] = int(state["next_id"]) + 1
        state["scheduled"].append(item)
        save_state()
        schedule_item(item)
        await event.reply(
            f"✅ Заплановано #{item['id']} через {mins} хв у chat {item['chat_id']}"
        )
        return

    if text == "/queue":
        await event.reply(fmt_queue(state["scheduled"]))
        return

    if text.startswith("/cancel "):
        arg = text.split(maxsplit=1)[1].strip()
        try:
            sid = int(arg)
        except ValueError:
            await event.reply("Формат: /cancel <id>")
            return
        task = scheduled_tasks.get(sid)
        if task and not task.done():
            task.cancel()
        before = len(state["scheduled"])
        state["scheduled"] = [x for x in state["scheduled"] if x["id"] != sid]
        save_state()
        if len(state["scheduled"]) < before:
            await event.reply(f"✅ Скасовано #{sid}")
        else:
            await event.reply("Немає такого id")
        return

    if text.startswith("/sendnow "):
        msg = text.split(maxsplit=1)[1]
        ok = await send_if_enabled(int(state["daily_chat_id"]), msg)
        if ok:
            await event.reply("✅ Відправлено зараз.")
        else:
            await event.reply("🛑 Не відправлено: sending=OFF")
        return

    if text == "/state":
        await event.reply(
            f"sending={'ON' if state['sending_enabled'] else 'OFF'}\n"
            f"daily={'ON' if state['daily_enabled'] else 'OFF'}\n"
            f"time={state['daily_hour']:02d}:{state['daily_minute']:02d}\n"
            f"daily_chat={state['daily_chat_id']}\n"
            f"queue={len(state['scheduled'])}"
        )
        return


async def main() -> None:
    print("Starting control_bot...", flush=True)
    load_state()

    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Session is not authorized. Regenerate SESSION_STRING.")

    me = await client.get_me()
    print(f"Logged in as: {me.id}", flush=True)
    print(f"Control chat: {CONTROL_CHAT_ID}", flush=True)
    print(
        f"Daily: {'ON' if state['daily_enabled'] else 'OFF'} at "
        f"{state['daily_hour']:02d}:{state['daily_minute']:02d}, "
        f"chat {state['daily_chat_id']}",
        flush=True,
    )

    for item in list(state["scheduled"]):
        schedule_item(item)

    asyncio.create_task(daily_loop())
    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(main())
