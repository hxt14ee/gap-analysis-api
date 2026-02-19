# Gap Analysis API

REST API + Streamlit UI для анализа разрывов между **Google AI Overview** и содержимым веб-страницы. Определяет, какие факты из AI Overview отсутствуют на странице, и генерирует SEO/GEO-рекомендации.

---

## Архитектура

```
POST /analyze
     ├─ Thordata SERP API  → текст AI Overview
     ├─ Trafilatura        → текст страницы
     ├─ LLM (Instructor)   → GapAnalysisResult (факты / пробелы / рекомендации)
     └─ PostgreSQL 16      → хранение (JSONB)

GET /history → последние 10 записей

Streamlit UI (port 8501) → форма ввода + визуализация результатов + история
```

### Стек

| Компонент | Технология |
|---|---|
| API | FastAPI + Uvicorn |
| БД | SQLAlchemy (async) + PostgreSQL 16 |
| SERP | Thordata ScraperAPI |
| Контент | Trafilatura |
| LLM | Instructor + OpenRouter / OpenAI |
| UI | Streamlit |

---

## Развёртывание на новом сервере

### Требования
- Docker Engine 24+ и Docker Compose v2

### 1. Клонировать и настроить

```bash
git clone <url>
cd gap-analysis-api
cp .env.example .env
```

Откройте `.env` и заполните:

```ini
SERPAPI_KEY=         # ключ из dashboard.thordata.com/serp-api
OPENROUTER_API_KEY=  # или OPENAI_API_KEY=
POSTGRES_PASSWORD=   # произвольный пароль (скопируйте в DATABASE_URL)
```

> **Важно:** `POSTGRES_USER`, `POSTGRES_PASSWORD` и `POSTGRES_DB` должны совпадать
> с соответствующими частями строки `DATABASE_URL`.

### 2. Запуск

```bash
docker compose up -d --build
```

| Сервис | Адрес |
|---|---|
| REST API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

```bash
docker compose logs -f api       # логи бэкенда
docker compose logs -f frontend  # логи UI
docker compose down              # остановить (данные сохраняются)
docker compose down -v           # остановить + удалить данные
```

---

## API

### `POST /analyze`

```json
{ "query": "gap analysis seo", "url": "https://example.com/" }
```

### `GET /history`

Возвращает последние 10 записей в том же формате, что и `/analyze`.

### `GET /health`

```json
{"status": "ok"}
```

### Статусы

| Статус | Описание |
|---|---|
| `completed` | Анализ выполнен |
| `aio_not_found` | AI Overview не найден |
| `scrape_failed` | Не удалось извлечь текст |
| `error` | Ошибка сервера |

---

## Streamlit UI

При запуске через Docker UI доступен на **http://localhost:8501**.

Локальный запуск (без Docker):
```bash
pip install -r requirements.txt
API_BASE_URL=http://localhost:8000 streamlit run frontend.py
```

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
OPENAI_BASE_URL=          # оставьте пустым
```
