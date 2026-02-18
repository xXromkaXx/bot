# telegram-vognyk-bot

Щодня відправляє `вогник` у Telegram-чат о 04:00 (Europe/Kyiv) через GitHub Actions.

## Файли

- `send_vognyk.py` — відправка повідомлення
- `control_bot.py` — постійно запущений userbot з командами керування
- `.github/workflows/vognyk.yml` — розклад запуску
- `.env.example` — приклад змінних

## Налаштування (безкоштовно)

1. Створи GitHub репозиторій і запуш цю папку.
2. У репозиторії: `Settings -> Secrets and variables -> Actions -> New repository secret`.
3. Додай секрети:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING`
   - `DAILY_CHAT_ID` = `986095695`
   - `TIMEZONE` = `Europe/Kyiv`
   - `TARGET_HOUR` = `4`
   - `TARGET_MINUTE` = `0`
4. У `Actions` запусти workflow `Daily Vognyk` через `Run workflow` для тесту.

## Важливо

- GitHub Actions не працює посекундно точно; затримка в кілька хвилин можлива.
- Якщо раніше світив `API_HASH` або `SESSION_STRING`, обов'язково перевипусти їх.

## Команди для `control_bot.py`

Запуск:

```bash
cd "/Users/romka/Documents/New project/telegram-vognyk-bot"
source ../.venv/bin/activate
set -a; source ../.env; set +a
python -u control_bot.py
```

Потрібна змінна `CONTROL_CHAT_ID` у `../.env` (це чат "Збережене", який ти вже визначив).

Команди (писати в control-чаті):

- `/help`
- `/sending on|off|status` — глобально вмикає/вимикає відправку
- `/daily on|off|status` — щоденна відправка `вогник`
- `/dailytime HH:MM` — час щоденної відправки
- `/dailychat <chat_id>` — куди слати щоденне/заплановане
- `/sendin <minutes> <text>` — запланувати повідомлення через N хв
- `/sendnow <text>` — відправити зараз
- `/queue` — черга запланованих
- `/cancel <id>` — скасувати заплановане
- `/state` — поточні налаштування
