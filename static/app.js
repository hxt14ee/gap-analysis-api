const BASE = '';

async function loadHistory() {
  const el = document.getElementById('history-list');
  try {
    const r = await fetch(`${BASE}/history`);
    const items = await r.json();
    if (!items.length) {
      el.innerHTML = '<p style="padding:1rem;font-size:.82rem;color:var(--muted)">История пуста.</p>';
      return;
    }
    el.innerHTML = items.map(i => {
      const sc = i.status === 'completed' ? 's-ok' : i.status === 'aio_not_found' ? 's-warn' : 's-err';
      const si = i.status === 'completed' ? '✅' : i.status === 'aio_not_found' ? '⚠️' : '❌';
      return `<div class="hist-item" onclick='showResult(${JSON.stringify(i)})'>
        <div class="hq">${esc(i.query)}</div>
        <div class="hu">${esc(i.url)}</div>
        <div class="hs"><span class="${sc}">${si} ${i.status}</span></div>
      </div>`;
    }).join('');
  } catch {
    el.innerHTML = '<p style="padding:1rem;font-size:.82rem;color:var(--muted)">API недоступен.</p>';
  }
}

async function runAnalysis() {
  const query = document.getElementById('query').value.trim();
  const url   = document.getElementById('url').value.trim();
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
    showResult(data);
    loadHistory();
  } catch (e) {
    toast(`Ошибка соединения: ${e.message}`);
  } finally {
    btn.disabled = false;
    spinner.classList.remove('active');
  }
}

function showResult(data) {
  window.scrollTo({ top: 0, behavior: 'smooth' });
  const res = document.getElementById('results');
  const status = data.status || '';
  const statusLabel = {
    completed: '✅ Завершён',
    aio_not_found: '⚠️ AI Overview не найден',
    scrape_failed: '❌ Не удалось получить текст',
    error: '❌ Ошибка сервера',
  }[status] || status;

  let html = `<span class="status-badge ${esc(status)}">${statusLabel}</span>`;

  if (status !== 'completed' || !data.analysis_result) {
    res.innerHTML = html;
    return;
  }

  const ar = data.analysis_result;
  if (ar.summary) html += `<div class="summary-box">📝 ${esc(ar.summary)}</div>`;

  const facts = ar.facts || [];
  const gaps  = ar.gaps  || [];
  const recs  = ar.recommendations || [];

  html += '<div class="two-col">';

  // Факты
  html += `<div class="card" style="margin:0"><p class="sec-title">📋 Факты из AI Overview (${facts.length})</p>`;
  facts.forEach(f => {
    const icon = f.present_in_page ? '✅' : '❌';
    html += `<div class="fact"><span class="fi">${icon}</span><span>${esc(f.statement)}</span></div>`;
  });
  html += '</div>';

  // Пробелы
  html += `<div class="card" style="margin:0"><p class="sec-title">🔍 Пробелы (${gaps.length})</p>`;
  gaps.forEach(g => {
    html += `<div class="gap"><div class="gt">${esc(g.topic)}</div><div class="gd">${esc(g.description)}</div></div>`;
  });
  html += '</div></div>';

  // Рекомендации
  const pl = { high: '🔴 Высокий', medium: '🟡 Средний', low: '🟢 Низкий' };
  html += `<div class="card"><p class="sec-title">💡 Рекомендации (${recs.length})</p>`;
  recs.forEach(r => {
    const p = r.priority || 'medium';
    html += `<div class="rec ${esc(p)}"><div class="rp">${pl[p] || p} приоритет</div>${esc(r.action)}</div>`;
  });
  html += '</div>';

  if (data.ai_overview_text) html += `<details><summary>Текст AI Overview</summary><pre>${esc(data.ai_overview_text)}</pre></details>`;
  if (data.page_text)        html += `<details><summary>Текст страницы</summary><pre>${esc(data.page_text)}</pre></details>`;

  res.innerHTML = html;
}

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 4000);
}

loadHistory();
