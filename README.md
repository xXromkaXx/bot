# telegram-vognyk-bot

Керується через Telegram-команди в Saved Messages і працює через GitHub Actions (кожні 5 хв).

## Файли

- `gh_poller.py` — читає команди з control-чату, виконує відкладені/щоденні відправки
- `.github/workflows/vognyk.yml` — розклад запуску
- `control_state.json` — стан (вкл/викл, черга, остання оброблена команда)
- `.env.example` — приклад змінних

## Налаштування (безкоштовно)

1. Створи GitHub репозиторій і запуш цю папку.
2. У репозиторії: `Settings -> Secrets and variables -> Actions -> New repository secret`.
3. Додай секрети:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING`
   - `CONTROL_CHAT_ID` (твій user id, рекомендовано: `1293715368`)
   - `DAILY_CHAT_ID` = `986095695`
   - `TIMEZONE` = `Europe/Kyiv`
4. У `Actions` запусти workflow `Daily Vognyk` через `Run workflow` для тесту.

## Важливо

- Команди з Telegram обробляються раз на 5 хв (не realtime).
- Якщо раніше світив `API_HASH` або `SESSION_STRING`, обов'язково перевипусти їх.

## Команди (писати в Saved Messages)

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
