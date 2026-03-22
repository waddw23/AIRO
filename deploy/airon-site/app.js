let API_BASE = resolveInitialApiBase();

const navs = [...document.querySelectorAll('.nav')];
const views = [...document.querySelectorAll('.view')];

const titleMap = {
  workspace: ['企业级电商 AI 工作台', '统一接入商家后台数据，进行实时分析与智能决策。'],
  connectors: ['商家数据接入', '配置平台 API 端口，建立统一数据层。'],
  analytics: ['实时分析中枢', '订单、投放、库存、客服事件流的统一分析。'],
  copilot: ['AIRON AI Copilot', '对话式分析与策略生成。']
};

let connectors = [];
let metricsTimer = null;
let eventsTimer = null;
let lastMetrics = null;
let lastEvents = [];
const animatedNumbers = new Map();

init().catch((err) => console.error(err));

async function init() {
  bindNav();
  bindPulse();
  bindConnectorForm();
  bindChat();
  bindApiBase();
  bindSearch();
  bindExportReport();
  bindQuickShortcuts();

  document.getElementById('apiBaseInput').value = API_BASE;

  if (!API_BASE) {
    const [title, subtitle] = titleMap.workspace;
    document.getElementById('title').textContent = title;
    document.getElementById('subtitle').textContent = `${subtitle} · 请先配置公网 API 地址`;
    setApiHealth('bad', 'API Not Set');
    toast('请先在右上角填写并应用公网 API 地址');
    return;
  }

  await Promise.all([loadConnectors(), refreshMetrics(), loadEvents(), checkApiHealth()]);

  metricsTimer = setInterval(refreshMetrics, 6000);
  eventsTimer = setInterval(async () => {
    await Promise.all([loadEvents(), checkApiHealth()]);
  }, 5000);
}

function bindNav() {
  navs.forEach((btn) => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      navs.forEach((n) => n.classList.toggle('active', n === btn));
      views.forEach((v) => v.classList.toggle('active', v.dataset.view === view));

      const [title, subtitle] = titleMap[view];
      document.getElementById('title').textContent = title;
      document.getElementById('subtitle').textContent = `${subtitle} · API: ${API_BASE}`;
    });
  });

  const [title, subtitle] = titleMap.workspace;
  document.getElementById('title').textContent = title;
  document.getElementById('subtitle').textContent = `${subtitle} · API: ${API_BASE}`;
}

function bindApiBase() {
  document.getElementById('applyApiBase').addEventListener('click', async () => {
    const next = document.getElementById('apiBaseInput').value.trim();
    if (!next) return;
    API_BASE = next.replace(/\/$/, '');
    localStorage.setItem('airon_api_base', API_BASE);
    await checkApiHealth();
    toast(`API 已切换到 ${API_BASE}`);

    try {
      await Promise.all([loadConnectors(), refreshMetrics(), loadEvents()]);
    } catch (err) {
      toast(`新 API 拉取失败: ${err.message}`);
    }

    const active = document.querySelector('.nav.active')?.dataset.view || 'workspace';
    const [title, subtitle] = titleMap[active];
    document.getElementById('title').textContent = title;
    document.getElementById('subtitle').textContent = `${subtitle} · API: ${API_BASE}`;
  });
}

async function checkApiHealth() {
  if (!API_BASE) {
    setApiHealth('bad', 'API Not Set');
    return;
  }

  setApiHealth('waiting', 'Checking');

  try {
    await api('/');
    setApiHealth('ok', 'API Online');
  } catch {
    setApiHealth('bad', 'API Offline');
  }
}

function bindPulse() {
  document.getElementById('demoPulse').addEventListener('click', async () => {
    await Promise.all([refreshMetrics(), loadEvents()]);
    toast('已刷新实时数据');
  });
}

function bindSearch() {
  document.getElementById('connectorSearch').addEventListener('input', renderConnectors);
}

async function loadConnectors() {
  const data = await api('/api/enterprise/connectors');
  connectors = data.items || [];
  renderConnectors();
  renderStatus();
}

function renderStatus() {
  const ul = document.getElementById('statusList');
  const ratioEl = document.getElementById('connectorRatio');
  const healthScoreEl = document.getElementById('healthScore');
  if (!connectors.length) {
    ul.innerHTML = '<li>暂无连接器，请在“数据接入”中新增。</li>';
    ratioEl.textContent = '0% 在线';
    if (healthScoreEl) healthScoreEl.textContent = '0%';
    return;
  }

  const connected = connectors.filter((c) => c.status === 'Connected').length;
  const ratio = ((connected / connectors.length) * 100).toFixed(1);
  ratioEl.textContent = `${ratio}% 在线`;
  if (healthScoreEl) healthScoreEl.textContent = `${ratio}%`;

  ul.innerHTML = connectors
    .slice(0, 6)
    .map((item) => {
      const cls = item.status === 'Connected' ? 'ok' : 'warn';
      return `<li>${item.platform}：<span class="badge-${cls}">${item.status}</span></li>`;
    })
    .join('');
}

function renderConnectors() {
  const tb = document.getElementById('connectorRows');
  const keyword = document.getElementById('connectorSearch').value.trim().toLowerCase();

  const list = connectors.filter((item) => {
    if (!keyword) return true;
    return `${item.platform} ${item.endpoint}`.toLowerCase().includes(keyword);
  });

  tb.innerHTML = list
    .map(
      (item) => `
      <tr>
        <td>${item.platform}</td>
        <td>${item.endpoint}</td>
        <td>${item.status}</td>
        <td>
          ${item.last_update || '-'}
          <button class="mini-test" data-id="${item.id}">测试</button>
        </td>
      </tr>`
    )
    .join('');

  [...document.querySelectorAll('.mini-test')].forEach((btn) => {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        await api(`/api/enterprise/connectors/${btn.dataset.id}/test`, {
          method: 'POST',
          body: JSON.stringify({ method: 'GET' })
        });
        await Promise.all([loadConnectors(), loadEvents(), refreshMetrics()]);
        toast('连接器测试完成');
      } catch (err) {
        toast(`连接测试失败: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function bindConnectorForm() {
  const form = document.getElementById('connectorForm');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
      platform: document.getElementById('type').value,
      endpoint: document.getElementById('endpoint').value.trim(),
      auth_type: document.getElementById('authType').value
    };

    if (!payload.endpoint) {
      toast('请填写 Endpoint');
      return;
    }

    try {
      await api('/api/enterprise/connectors', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      form.reset();
      await Promise.all([loadConnectors(), loadEvents(), refreshMetrics()]);
      toast('连接器已新增');
    } catch (err) {
      toast(`新增失败: ${err.message}`);
    }
  });
}

async function refreshMetrics() {
  const data = await api('/api/enterprise/metrics');
  const kpis = data.kpis || {};
  lastMetrics = kpis;

  setNum('gmv', kpis.gmv || 0, '¥ ');
  setNum('aicvr', kpis.aicvr || 0, '', '%');
  setNum('fcr', kpis.fcr || 0, '', '%');
  setNum('risk', kpis.risk || 0);
  updateDecisionCount();

  renderBars(data.channels || []);
}

function setNum(id, n, prefix = '', suffix = '') {
  const el = document.getElementById(id);
  if (!el) return;

  const target = Number(n) || 0;
  const decimals = Number.isInteger(target) ? 0 : 1;
  const from = animatedNumbers.get(id) ?? target;
  animateValue(el, from, target, {
    prefix,
    suffix,
    decimals
  });
  animatedNumbers.set(id, target);
}

function renderBars(channels) {
  const box = document.getElementById('bars');
  if (!channels.length) {
    box.innerHTML = '<p class="muted">暂无实时分析数据</p>';
    return;
  }

  box.innerHTML = channels
    .map(
      (item) => `<div class="bar"><span>${item.label}</span><div class="track"><div class="fill" style="width:${item.value}%"></div></div><strong>${item.value}%</strong></div>`
    )
    .join('');
}

async function loadEvents() {
  const data = await api('/api/enterprise/events');
  const list = document.getElementById('events');
  const items = data.items || [];
  lastEvents = items;

  list.innerHTML = items.length
    ? items.map((item) => `<li>${item}</li>`).join('')
    : '<li>暂无事件</li>';

  updateDecisionCount();
}

function bindChat() {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const chat = document.getElementById('chat');
  const cards = document.getElementById('strategyCards');
  const actions = document.getElementById('aironActions');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    push('user', text);
    input.value = '';
    const pending = push('ai', 'AIRON 分析中...');

    try {
      const data = await api('/api/enterprise/airon/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text, user_id: 'user9093316760' })
      });

      const answer = data.answer || 'AIRON 无返回内容。';
      pending.textContent = answer;
      renderStrategyCards(answer, cards, actions);
      await loadEvents();
    } catch (err) {
      pending.textContent = `AIRON 调用失败：${err.message}`;
    }

    chat.scrollTop = chat.scrollHeight;
  });

  document.getElementById('promptSuggestions').addEventListener('click', (e) => {
    const btn = e.target.closest('.suggest');
    if (!btn) return;
    input.value = btn.textContent.trim();
    input.focus();
  });

  function push(role, text) {
    const node = document.createElement('div');
    node.className = `bubble ${role}`;
    node.textContent = text;
    chat.appendChild(node);
    chat.scrollTop = chat.scrollHeight;
    return node;
  }
}

function renderStrategyCards(answer, cards, actions) {
  cards.innerHTML = '';
  actions.innerHTML = '';

  const parsed = parseMaybeJSON(answer);
  if (!parsed || typeof parsed !== 'object') {
    actions.innerHTML = '<li>未检测到结构化结果，已展示原始回复。</li>';
    return;
  }

  const block = [];

  if (parsed.summary) {
    block.push(card('策略摘要', `<p>${escapeHtml(parsed.summary)}</p>`));
    actions.innerHTML += `<li>${escapeHtml(parsed.summary)}</li>`;
  }

  if (Array.isArray(parsed.options) && parsed.options.length) {
    const list = parsed.options
      .map((opt) => {
        const pros = Array.isArray(opt['优点']) ? opt['优点'].map((x) => `<li>${escapeHtml(x)}</li>`).join('') : '';
        const cons = Array.isArray(opt['缺点']) ? opt['缺点'].map((x) => `<li>${escapeHtml(x)}</li>`).join('') : '';
        const name = escapeHtml(opt['方案'] || '方案');
        return `<li><strong>${name}</strong><ul>${pros}${cons}</ul></li>`;
      })
      .join('');
    block.push(card('策略方案', `<ul>${list}</ul>`));
  }

  if (parsed['推荐方案']) {
    block.push(card('推荐方案', `<p>${escapeHtml(parsed['推荐方案'])}</p>`));
    actions.innerHTML += `<li>推荐：${escapeHtml(parsed['推荐方案'])}</li>`;
  }

  if (parsed['下一步建议']) {
    block.push(card('下一步建议', `<p>${escapeHtml(parsed['下一步建议'])}</p>`));
    actions.innerHTML += `<li>${escapeHtml(parsed['下一步建议'])}</li>`;
  }

  cards.innerHTML = block.join('');
  if (!actions.innerHTML.trim()) {
    actions.innerHTML = '<li>已返回结构化建议。</li>';
  }
}

function card(title, content) {
  return `<article class="strategy-card"><h4>${title}</h4>${content}</article>`;
}

function parseMaybeJSON(text) {
  if (!text) return null;
  const trimmed = String(text).trim();

  try {
    return JSON.parse(trimmed);
  } catch {}

  const first = trimmed.indexOf('{');
  const last = trimmed.lastIndexOf('}');
  if (first >= 0 && last > first) {
    const candidate = trimmed.slice(first, last + 1);
    try {
      return JSON.parse(candidate);
    } catch {}
  }
  return null;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function bindExportReport() {
  document.getElementById('exportReport').addEventListener('click', () => {
    const payload = {
      generated_at: new Date().toISOString(),
      api_base: API_BASE,
      metrics: lastMetrics,
      connectors,
      events: lastEvents
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `airon-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('日报已导出');
  });
}

function bindQuickShortcuts() {
  document.addEventListener('keydown', (e) => {
    const key = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && key === 'k') {
      e.preventDefault();
      const copilotNav = document.querySelector('.nav[data-view="copilot"]');
      copilotNav?.click();
      document.getElementById('chatInput').focus();
    }
  });

  document.getElementById('clearView').addEventListener('click', () => {
    document.getElementById('events').innerHTML = '<li>视图已清空（不影响服务端事件）</li>';
    toast('已清空当前事件视图');
  });
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 1600);
}

function updateDecisionCount() {
  const el = document.getElementById('decisionCount');
  if (!el) return;
  const risk = Number(lastMetrics?.risk || 0);
  const value = Math.max(0, lastEvents.length * 3 + connectors.length * 2 - risk);
  el.textContent = value.toLocaleString('zh-CN');
}

function animateValue(el, from, to, { prefix = '', suffix = '', decimals = 0 } = {}) {
  const start = performance.now();
  const duration = 480;
  const delta = to - from;

  const tick = (now) => {
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    const current = from + delta * eased;
    const numText =
      decimals > 0 ? current.toFixed(decimals) : Math.round(current).toLocaleString('zh-CN');
    el.textContent = `${prefix}${numText}${suffix}`;
    if (p < 1) requestAnimationFrame(tick);
  };

  requestAnimationFrame(tick);
}

async function api(path, init = {}) {
  if (!API_BASE) {
    throw new Error('请先配置公网 API 地址');
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {})
    },
    ...init
  });

  const text = await resp.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch {
    parsed = { detail: text };
  }

  if (!resp.ok) {
    throw new Error(parsed.detail || `HTTP ${resp.status}`);
  }
  return parsed;
}

function setApiHealth(status, text) {
  const health = document.getElementById('apiHealth');
  health.className = `health ${status}`;
  health.textContent = text;
}

function resolveInitialApiBase() {
  const fromStorage = localStorage.getItem('airon_api_base');
  if (fromStorage) return fromStorage;

  const fromQuery = new URLSearchParams(window.location.search).get('api');
  if (fromQuery) return fromQuery.replace(/\/$/, '');

  const fromRuntime = window.AIRON_RUNTIME_CONFIG?.apiBase;
  if (typeof fromRuntime === 'string' && fromRuntime.trim()) {
    return fromRuntime.trim().replace(/\/$/, '');
  }

  const isLocal =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isLocal ? 'http://localhost:8000' : '';
}

window.addEventListener('beforeunload', () => {
  if (metricsTimer) clearInterval(metricsTimer);
  if (eventsTimer) clearInterval(eventsTimer);
});
