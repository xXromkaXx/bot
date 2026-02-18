import os
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
DAILY_CHAT_ID = int(os.environ.get("DAILY_CHAT_ID", "986095695"))
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Kyiv")
TARGET_HOUR = int(os.environ.get("TARGET_HOUR", "4"))
TARGET_MINUTE = int(os.environ.get("TARGET_MINUTE", "0"))
MESSAGE_TEXT = os.environ.get("MESSAGE_TEXT", "вогник")
FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"


def should_send_now() -> bool:
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE


def main() -> None:
    if not FORCE_SEND and not should_send_now():
        print("Skip: not target local time yet")
        return

    with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        client.send_message(DAILY_CHAT_ID, MESSAGE_TEXT)
        print(f"Sent '{MESSAGE_TEXT}' successfully")


if __name__ == "__main__":
    main()
