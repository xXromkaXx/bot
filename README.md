# telegram-vognyk-bot

Щодня відправляє `вогник` у Telegram-чат о 04:00 (Europe/Kyiv) через GitHub Actions.

## Файли

- `send_vognyk.py` — відправка повідомлення
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
