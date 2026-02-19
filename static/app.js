const BASE = '';

// Полный массив истории для фильтрации
let historyData = [];

// ── Вкладки ────────────────────────────────────────────────────────────────

function switchTab(id, btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${id}`).classList.add('active');
    if (id === 'archive') loadHistory();
}

// ── История ────────────────────────────────────────────────────────────────

async function loadHistory() {
    const el = document.getElementById('history-list');
    el.innerHTML = '<p class="empty-msg">Загрузка…</p>';
    try {
        const r = await fetch(`${BASE}/history`);
        historyData = await r.json();
        renderHistory(historyData);
    } catch {
        el.innerHTML = '<p class="empty-msg">API недоступен.</p>';
    }
}

function filterHistory() {
    const q = document.getElementById('search').value.trim().toLowerCase();
    const filtered = q
        ? historyData.filter(i => i.query.toLowerCase().includes(q) || i.url.toLowerCase().includes(q))
        : historyData;
    renderHistory(filtered);
}

function renderHistory(items) {
    const el = document.getElementById('history-list');
    if (!items.length) {
        el.innerHTML = '<p class="empty-msg">Ничего не найдено.</p>';
        return;
    }

    el.innerHTML = items.map((item, idx) => {
        const sc = statusClass(item.status);
        const label = statusLabel(item.status);
        const date = formatDate(item.timestamp);
        const ar = item.analysis_result;

        // Внутреннее содержимое карточки
        let body = `<div class="hist-url">${esc(item.url)}</div>`;
        body += `<div class="hist-date">📅 ${date}</div>`;

        if (item.ai_overview_text) {
            body += `<details><summary>Текст AI Overview</summary><pre>${esc(item.ai_overview_text)}</pre></details>`;
        }

        if (ar) {
            const facts = ar.facts || [];
            const gaps = ar.gaps || [];
            const recs = ar.recommendations || [];

            if (ar.summary) {
                body += `<div class="summary-box" style="margin-bottom:1rem">📝 ${esc(ar.summary)}</div>`;
            }

            body += '<div class="two-col">';

            // Факты
            body += `<div><p class="sec-title">📋 Факты (${facts.length})</p>`;
            facts.forEach(f => {
                const icon = f.present_in_page ? '✅' : '❌';
                body += `<div class="fact"><span class="fi">${icon}</span><span>${esc(f.statement)}</span></div>`;
            });
            body += '</div>';

            // Пробелы
            body += `<div><p class="sec-title">🔍 Пробелы (${gaps.length})</p>`;
            gaps.forEach(g => {
                body += `<div class="gap"><div class="gt">${esc(g.topic)}</div><div class="gd">${esc(g.description)}</div></div>`;
            });
            body += '</div></div>';

            // Рекомендации
            const pl = { high: '🔴 Высокий', medium: '🟡 Средний', low: '🟢 Низкий' };
            body += `<p class="sec-title" style="margin-top:.75rem">💡 Рекомендации (${recs.length})</p>`;
            recs.forEach(r => {
                const p = r.priority || 'medium';
                body += `<div class="rec ${esc(p)}"><div class="rp">${pl[p] || p} приоритет</div>${esc(r.action)}</div>`;
            });
        }

        return `
      <div class="hist-card" id="hcard-${idx}">
        <div class="hist-toggle" onclick="toggleCard(${idx})">
          <div class="hist-title">${esc(item.query)}</div>
          <div class="hist-meta">
            <span class="${sc}">${label}</span>
            <span class="hist-arrow">▼</span>
          </div>
        </div>
        <div class="hist-body">${body}</div>
      </div>`;
    }).join('');
}

function toggleCard(idx) {
    document.getElementById(`hcard-${idx}`).classList.toggle('open');
}

// ── Анализ ─────────────────────────────────────────────────────────────────

async function runAnalysis() {
    const query = document.getElementById('query').value.trim();
    const url = document.getElementById('url').value.trim();
    if (!query || !url) { toast('Введите запрос и URL.'); return; }

    const btn = document.getElementById('run-btn');
    const spinner = document.getElementById('spinner');
    btn.disabled = true;
    spinner.classList.add('active');
    document.getElementById('results').innerHTML = '';

    try {
        const r = await fetch(`${BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, url }),
        });
        const data = await r.json();
        if (!r.ok) { toast(data.detail || `HTTP ${r.status}`); return; }
        renderResult(data);
    } catch (e) {
        toast(`Ошибка соединения: ${e.message}`);
    } finally {
        btn.disabled = false;
        spinner.classList.remove('active');
    }
}

function renderResult(data) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const res = document.getElementById('results');
    const status = data.status || '';
    const label = statusLabel(status);
    const sc = statusClass(status);

    let html = `<span class="status-badge ${esc(status)}">${label}</span>`;

    if (status !== 'completed' || !data.analysis_result) {
        res.innerHTML = html;
        return;
    }

    const ar = data.analysis_result;
    const facts = ar.facts || [];
    const gaps = ar.gaps || [];
    const recs = ar.recommendations || [];

    if (ar.summary) html += `<div class="summary-box">📝 ${esc(ar.summary)}</div>`;

    html += '<div class="two-col">';
    html += `<div class="card" style="margin:0"><p class="sec-title">📋 Факты из AI Overview (${facts.length})</p>`;
    facts.forEach(f => {
        const icon = f.present_in_page ? '✅' : '❌';
        html += `<div class="fact"><span class="fi">${icon}</span><span>${esc(f.statement)}</span></div>`;
    });
    html += '</div>';

    html += `<div class="card" style="margin:0"><p class="sec-title">🔍 Пробелы (${gaps.length})</p>`;
    gaps.forEach(g => {
        html += `<div class="gap"><div class="gt">${esc(g.topic)}</div><div class="gd">${esc(g.description)}</div></div>`;
    });
    html += '</div></div>';

    const pl = { high: '🔴 Высокий', medium: '🟡 Средний', low: '🟢 Низкий' };
    html += `<div class="card"><p class="sec-title">💡 Рекомендации (${recs.length})</p>`;
    recs.forEach(r => {
        const p = r.priority || 'medium';
        html += `<div class="rec ${esc(p)}"><div class="rp">${pl[p] || p} приоритет</div>${esc(r.action)}</div>`;
    });
    html += '</div>';

    if (data.ai_overview_text) {
        html += `<details><summary>Текст AI Overview</summary><pre>${esc(data.ai_overview_text)}</pre></details>`;
    }

    res.innerHTML = html;
}

// ── Утилиты ────────────────────────────────────────────────────────────────

function statusLabel(s) {
    return { completed: '✅ Завершён', aio_not_found: '⚠️ Нет AI Overview', scrape_failed: '❌ Ошибка скрапинга', error: '❌ Ошибка' }[s] || s;
}

function statusClass(s) {
    return { completed: 's-ok', aio_not_found: 's-warn', error: 's-err', scrape_failed: 's-err' }[s] || '';
}

function formatDate(ts) {
    if (!ts) return '—';
    return new Date(ts).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 4000);
}
