# Gap Analysis API

REST API + встроенный веб-интерфейс для анализа разрывов между **Google AI Overview** и содержимым веб-страницы.

```
git clone https://github.com/hxt14ee/gap-analysis-api
```

---

## Архитектура

```
POST /analyze  →  Thordata → Trafilatura → LLM → PostgreSQL
GET  /history  →  последние 10 записей
GET  /         →  веб-UI
```

| Компонент | Технология |
|---|---|
| API + UI | FastAPI + Uvicorn · порт 8000 |
| БД | SQLAlchemy async + PostgreSQL 16 |
| SERP | Thordata ScraperAPI |
| Контент | Trafilatura |
| LLM | Instructor + OpenRouter / OpenAI |

---

## Развёртывание

### Требования
Docker Engine 24+ и Docker Compose v2.

### 1. Клонировать

```bash
git clone https://github.com/hxt14ee/gap-analysis-api
cd gap-analysis-api
cp .env.example .env
```

### 2. Настроить `.env`

Откройте `.env` и заполните обязательные поля:

```ini
POSTGRES_USER=gapuser        # имя пользователя БД
POSTGRES_PASSWORD=gappassword # пароль БД
POSTGRES_DB=gapanalysis

# !! Хост "db" не меняйте — это внутреннее имя контейнера
DATABASE_URL=postgresql+asyncpg://gapuser:gappassword@db:5432/gapanalysis

SERPAPI_KEY=       # ключ из dashboard.thordata.com/serp-api
OPENROUTER_API_KEY= # или OPENAI_API_KEY=
```

> **Важно — смена логина/пароля БД:**
> Если вы меняете `POSTGRES_USER` или `POSTGRES_PASSWORD`, нужно обновить **три места одновременно**:
> 1. `POSTGRES_USER` / `POSTGRES_PASSWORD` в `.env`
> 2. Строку `DATABASE_URL` в `.env`
> 3. Строку `DATABASE_URL` в `docker-compose.yml` → секция `environment` сервиса `api`:
>    ```yaml
>    - DATABASE_URL=postgresql+asyncpg://ВАШ_ЛОГИН:ВАШ_ПАРОЛЬ@db:5432/ВАШ_БД
>    ```

### 3. Запуск

```bash
docker compose up -d --build
```

---

## Адреса после запуска

| Что | Адрес |
|---|---|
| 🖥️ Веб-интерфейс | http://localhost:8000 |
| 📖 Swagger / OpenAPI | http://localhost:8000/docs |

---

## API

### `POST /analyze`
```json
{"query": "gap analysis seo", "url": "https://example.com/"}
```

### `GET /history`
Последние 10 записей (тот же формат ответа, что и `/analyze`).

### Статусы

| Статус | Описание |
|---|---|
| `completed` | Анализ выполнен |
| `aio_not_found` | AI Overview не найден |
| `scrape_failed` | Не удалось извлечь текст страницы |
| `error` | Внутренняя ошибка |

---

## Смена LLM

**OpenRouter (по умолчанию):**
```ini
OPENROUTER_API_KEY=sk-or-...
OPENAI_MODEL=openai/gpt-4o-mini
```

**OpenAI напрямую:**
```ini
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
```

---

## Управление

```bash
docker compose logs -f api   # логи бэкенда
docker compose down          # остановить (данные сохраняются)
docker compose down -v       # остановить и удалить данные БД
```
