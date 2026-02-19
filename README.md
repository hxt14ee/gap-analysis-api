# Gap Analysis API

REST API для анализа разрывов между **Google AI Overview** и содержимым конкретной веб-страницы. Сервис автоматически определяет, какие факты из AI Overview отсутствуют на странице, и генерирует конкретные SEO-рекомендации для устранения этих пробелов.

---

## Архитектура

```
POST /analyze
     │
     ├─ 1. AIO Client   (services/aio_client.py)  — mock; в продакшне — реальный API
     │       └─ возвращает текст AI Overview (или статус "aio_not_found")
     │
     ├─ 2. Scraper       (services/scraper.py)     — Trafilatura
     │       └─ извлекает основной текст со страницы по URL
     │
     ├─ 3. Analyzer      (services/analyzer.py)    — Instructor + LLM
     │       └─ возвращает GapAnalysisResult (факты / пробелы / рекомендации)
     │
     └─ 4. PostgreSQL    (models.py)               — хранит всё, включая JSONB-результат
```

### Технологический стек

| Компонент | Технология |
|---|---|
| Веб-фреймворк | FastAPI + Uvicorn |
| ORM / БД | SQLAlchemy (async) + PostgreSQL 16 |
| Извлечение контента | Trafilatura |
| Структурированный вывод LLM | Instructor + OpenAI / OpenRouter |
| Контейнеризация | Docker + Docker Compose |

### Структура проекта

```
.
├── main.py                  # FastAPI приложение, маршруты
├── database.py              # Async SQLAlchemy движок и сессия
├── models.py                # ORM-модель AnalysisRequest
├── schemas.py               # Pydantic-схемы запросов и ответов LLM
├── services/
│   ├── aio_client.py        # Mock-клиент для получения AI Overview
│   ├── scraper.py           # Парсер страниц (Trafilatura)
│   └── analyzer.py         # Gap-анализатор (Instructor + LLM)
├── Dockerfile               # Образ для API-сервиса
├── docker-compose.yml       # Оркестрация API + PostgreSQL
├── .env.example             # Пример переменных окружения
└── requirements.txt         # Зависимости Python
```

---

## Быстрый старт (на новом сервере)

### Требования

- Docker Engine 24+
- Docker Compose v2

### 1. Клонировать репозиторий

```bash
git clone <ваш-репозиторий-url>
cd gap-analysis-api
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
```

Откройте `.env` и при необходимости укажите ключ LLM:

```ini
# Для работы с реальным LLM (см. раздел ниже)
OPENAI_API_KEY=sk-...
# или
OPENROUTER_API_KEY=sk-or-...
```

Без ключей сервис запустится в **режиме mock** и будет возвращать детерминированные тестовые данные.

### 3. Запустить систему

```bash
docker compose up -d --build
```

Эта команда:
- Соберёт образ FastAPI из `Dockerfile`
- Поднимет контейнер PostgreSQL 16
- Дождётся готовности БД (healthcheck) и запустит API

API будет доступен по адресу: **http://localhost:8000**

Интерактивная документация (Swagger UI): **http://localhost:8000/docs**

### 4. Просмотр логов

```bash
docker compose logs -f api
```

### 5. Остановить сервис

```bash
docker compose down
# Со сбросом данных БД:
docker compose down -v
```

---

## Справка по API

### `GET /health`

Проверка работоспособности сервиса.

**Ответ 200**
```json
{"status": "ok"}
```

---

### `POST /analyze`

Запуск полного цикла gap-анализа.

**Тело запроса**
```json
{
  "query": "python fastapi tutorial",
  "url": "https://fastapi.tiangolo.com/"
}
```

| Поле | Тип | Описание |
|---|---|---|
| `query` | string | Поисковый запрос (используется для получения AI Overview) |
| `url` | string (URL) | Адрес страницы для сравнения |

**Ответ 201 — успешный анализ (`status: completed`)**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "completed",
  "query": "python fastapi tutorial",
  "url": "https://fastapi.tiangolo.com/",
  "timestamp": "2026-02-19T15:48:00Z",
  "ai_overview_text": "FastAPI is a modern ...",
  "page_text": "Welcome to FastAPI ...",
  "analysis_result": {
    "facts": [
      {
        "statement": "FastAPI поддерживает нативный async ...",
        "present_in_page": true
      }
    ],
    "gaps": [
      {
        "topic": "Сравнение производительности",
        "description": "AI Overview упоминает бенчмарки, страница их не содержит."
      }
    ],
    "recommendations": [
      {
        "action": "Добавить раздел с таблицей сравнения производительности.",
        "priority": "high"
      }
    ],
    "summary": "Страница хорошо покрывает основы, но ..."
  }
}
```

**Ответ 201 — AI Overview не найден (`status: aio_not_found`)**
```json
{
  "id": "...",
  "status": "aio_not_found",
  "analysis_result": null
}
```

### Статусы записей

| Статус | Описание |
|---|---|
| `pending` | Запись создана, пайплайн запускается |
| `aio_not_found` | AI Overview для данного запроса не найден |
| `scrape_failed` | Trafilatura не смогла извлечь текст со страницы |
| `completed` | Анализ выполнен и сохранён |
| `error` | Непредвиденная ошибка сервера |

---

## Тестирование через curl

```bash
# Успешный анализ (запрос совпадает с mock-корпусом: "python fastapi", "gap analysis", "machine learning")
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "python fastapi tutorial", "url": "https://fastapi.tiangolo.com/"}'

# Кейс "AI Overview не найден"
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "запрос без mock-данных", "url": "https://example.com/"}'

# Healthcheck
curl http://localhost:8000/health
```

---

## Подключение реального LLM

По умолчанию сервис работает с **встроенным mock-клиентом** — никаких внешних запросов не выполняется.

### OpenAI

```ini
# .env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### OpenRouter

OpenRouter предоставляет доступ к большому числу моделей (Claude, Gemini, Llama и др.) через единый OpenAI-совместимый API.

1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai) и получите ключ.
2. Обновите `services/analyzer.py`: замените инициализацию клиента:

```python
from openai import AsyncOpenAI

client = instructor.from_openai(
    AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    ),
    mode=instructor.Mode.JSON,
)
MODEL = "openai/gpt-4o-mini"  # или любая другая модель OpenRouter
```

3. Укажите ключ в `.env`:

```ini
OPENROUTER_API_KEY=sk-or-...
OPENAI_MODEL=openai/gpt-4o-mini
```

4. Пересоберите контейнер:

```bash
docker compose up -d --build
```
