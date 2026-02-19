# Gap Analysis API

REST API + встроенный веб-интерфейс для анализа разрывов между **Google AI Overview** и содержимым веб-страницы.

---

## Архитектура

```
POST /analyze
     ├─ Thordata SERP API  → текст AI Overview
     ├─ Trafilatura        → текст страницы
     ├─ LLM (Instructor)   → факты / пробелы / рекомендации
     └─ PostgreSQL 16      → хранение

GET /history → последние 10 записей
GET /        → встроенный веб-UI
```

| Компонент | Технология |
|---|---|
| API + UI | FastAPI + Uvicorn (port 8000) |
| БД | SQLAlchemy async + PostgreSQL 16 |
| SERP | Thordata ScraperAPI |
| Контент | Trafilatura |
| LLM | Instructor + OpenRouter / OpenAI |

---

## Развёртывание

### Требования
Docker Engine 24+ и Docker Compose v2.

### 1. Настроить `.env`

```bash
git clone <url> && cd gap-analysis-api
cp .env.example .env
```

Заполните в `.env`:
```ini
SERPAPI_KEY=         # ключ из dashboard.thordata.com/serp-api
OPENROUTER_API_KEY=  # или OPENAI_API_KEY=
POSTGRES_PASSWORD=   # произвольный пароль (он же в DATABASE_URL)
```

> **Важно:** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` должны совпадать
> с соответствующими частями строки `DATABASE_URL`.

### 2. Запуск

```bash
docker compose up -d --build
```

| Адрес | Назначение |
|---|---|
| http://localhost:8000 | Веб-UI + REST API |
| http://localhost:8000/docs | Swagger |

```bash
docker compose logs -f api   # логи
docker compose down          # остановить
docker compose down -v       # остановить + удалить данные
```

---

## API

### `POST /analyze`
```json
{"query": "gap analysis seo", "url": "https://example.com/"}
```

### `GET /history`
Последние 10 записей (тот же формат, что `/analyze`).

### Статусы ответа

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

**OpenAI:**
```ini
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
```
