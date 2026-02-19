"""
Streamlit UI для Gap Analysis API.

Запуск локально: streamlit run frontend.py
Переменная окружения API_BASE_URL задаёт адрес бэкенда.
"""
import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Gap Analysis", page_icon="🔍", layout="wide")

# ── Стили ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main { background-color: #0f1116; }
    .block-container { padding-top: 2rem; }
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 2rem; font-weight: 600; width: 100%;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }
    .metric-card {
        background: #1e2030; border-radius: 12px;
        padding: 1.2rem; border-left: 4px solid #6366f1;
        margin-bottom: 0.8rem;
    }
    .gap-card {
        background: #1e2030; border-radius: 12px;
        padding: 1.2rem; border-left: 4px solid #f59e0b;
        margin-bottom: 0.8rem;
    }
    .rec-high  { border-left-color: #ef4444 !important; }
    .rec-medium{ border-left-color: #f59e0b !important; }
    .rec-low   { border-left-color: #22c55e !important; }
    .history-item {
        background: #1e2030; border-radius: 8px; padding: 0.7rem 1rem;
        margin-bottom: 0.4rem; cursor: pointer;
        border-left: 3px solid #6366f1;
    }
    .status-completed { color: #22c55e; font-weight: 600; }
    .status-aio_not_found { color: #f59e0b; font-weight: 600; }
    .status-error { color: #ef4444; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Вспомогательные функции ──────────────────────────────────────────────────

def fetch_history() -> list:
    try:
        r = requests.get(f"{API_BASE_URL}/history", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def run_analysis(query: str, url: str) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"query": query, "url": url},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API ошибка {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        st.error(f"Ошибка соединения с API: {e}")
    return None


def priority_class(priority: str) -> str:
    return {"high": "rec-high", "medium": "rec-medium", "low": "rec-low"}.get(priority, "rec-medium")


def render_results(data: dict) -> None:
    """Отображает результат анализа."""
    st.divider()

    status = data.get("status", "")
    status_map = {
        "completed": ("✅ Анализ завершён", "status-completed"),
        "aio_not_found": ("⚠️ AI Overview не найден", "status-aio_not_found"),
        "scrape_failed": ("❌ Не удалось получить текст страницы", "status-error"),
        "error": ("❌ Ошибка сервера", "status-error"),
    }
    label, css = status_map.get(status, (f"Статус: {status}", ""))
    st.markdown(f'<p class="{css}">{label}</p>', unsafe_allow_html=True)

    if status != "completed" or not data.get("analysis_result"):
        return

    result = data["analysis_result"]
    summary = result.get("summary", "")
    if summary:
        st.info(f"**Резюме:** {summary}")

    col1, col2 = st.columns(2)

    # Факты
    with col1:
        facts = result.get("facts", [])
        st.markdown(f"### 📋 Факты из AI Overview ({len(facts)})")
        for f in facts:
            icon = "✅" if f.get("present_in_page") else "❌"
            label = "присутствует" if f.get("present_in_page") else "отсутствует"
            st.markdown(
                f'<div class="metric-card">{icon} <b>{label}</b><br>{f["statement"]}</div>',
                unsafe_allow_html=True,
            )

    # Пробелы
    with col2:
        gaps = result.get("gaps", [])
        st.markdown(f"### 🔍 Пробелы в контенте ({len(gaps)})")
        for g in gaps:
            st.markdown(
                f'<div class="gap-card"><b>{g["topic"]}</b><br>{g["description"]}</div>',
                unsafe_allow_html=True,
            )

    # Рекомендации
    recs = result.get("recommendations", [])
    st.markdown(f"### 💡 Рекомендации ({len(recs)})")
    priority_labels = {"high": "🔴 Высокий", "medium": "🟡 Средний", "low": "🟢 Низкий"}
    for rec in recs:
        p = rec.get("priority", "medium")
        css = priority_class(p)
        p_label = priority_labels.get(p, p)
        st.markdown(
            f'<div class="metric-card {css}"><b>{p_label} приоритет</b><br>{rec["action"]}</div>',
            unsafe_allow_html=True,
        )

    # Исходные тексты (расширяемые)
    with st.expander("Текст AI Overview"):
        st.text(data.get("ai_overview_text", "—"))
    with st.expander("Текст страницы"):
        st.text(data.get("page_text", "—"))


# ── Sidebar: история ─────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🕓 История запросов")

    if st.button("🔄 Обновить"):
        st.rerun()

    history = fetch_history()
    if not history:
        st.caption("История пуста или API недоступен.")
    else:
        for item in history:
            status_icon = {
                "completed": "✅",
                "aio_not_found": "⚠️",
                "error": "❌",
                "scrape_failed": "❌",
                "pending": "⏳",
            }.get(item.get("status", ""), "❓")

            label = f"{status_icon} {item['query'][:35]}"
            if st.button(label, key=str(item["id"])):
                st.session_state["loaded_result"] = item


# ── Основной экран ───────────────────────────────────────────────────────────

st.markdown("# 🔍 Gap Analysis")
st.markdown("Сравни содержимое страницы с тем, что Google показывает в **AI Overview**.")

with st.form("analyze_form"):
    query = st.text_input(
        "Поисковый запрос",
        placeholder="например: как похудеть за месяц",
    )
    url = st.text_input(
        "URL страницы",
        placeholder="https://example.com/your-article",
    )
    submitted = st.form_submit_button("▶ Запустить анализ")

if submitted:
    if not query or not url:
        st.warning("Введите запрос и URL.")
    else:
        with st.spinner("Получаем AI Overview и анализируем страницу…"):
            result = run_analysis(query, url)
        if result:
            st.session_state["loaded_result"] = result

# Показываем результат — либо из формы, либо из истории
if "loaded_result" in st.session_state:
    render_results(st.session_state["loaded_result"])
