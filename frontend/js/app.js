import { getConfig, saveConfig, sendToAIRON } from './cozeClient.js';

const tabs = [...document.querySelectorAll('.tab')];
const views = [...document.querySelectorAll('.view')];
const kpiRow = document.getElementById('kpiRow');
const channelBars = document.getElementById('channelBars');
const skuList = document.getElementById('skuList');
const chatWindow = document.getElementById('chatWindow');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const promptText = document.getElementById('promptText');

const channels = [
  { name: '淘宝', value: 92 },
  { name: '抖音', value: 84 },
  { name: '私域', value: 73 },
  { name: '京东', value: 68 }
];

const skus = [
  { name: 'AIRON 静音破壁机 Pro', demand: 96, stock: '偏低', action: '提高补货频次，保持加价空间' },
  { name: '智能空气炸锅 Mini', demand: 81, stock: '健康', action: '维持爆款节奏，增加套装购' },
  { name: '便携电热杯 Lite', demand: 66, stock: '偏高', action: '做内容种草+限时券清理库存' }
];

const structuredAnswer = {
  summary: '建议将预算向短视频与高意向搜索倾斜，并在私域做老客召回。',
  strategy: '预热期 3 天拉新，爆发期 2 天强转化，返场期 2 天做复购闭环。',
  risk: '库存与客服压力同步上升，建议提前启用 AI 自动分流与补货阈值。'
};

renderKpi();
renderChannels();
renderSkus();
bindTabs();
bindConfig();
bindChat();
loadConfig();

if (new URLSearchParams(location.search).get('demo') === '1') {
  startKeynote();
}

document.getElementById('demoBtn').addEventListener('click', startKeynote);

function renderKpi() {
  const items = [
    { label: '内容投放转化', value: '+18.2%' },
    { label: '高价值客群增长', value: '+12.7%' },
    { label: '智能客服节省', value: '39h/天' }
  ];

  kpiRow.innerHTML = items
    .map((item) => `<div class="kpi"><small>${item.label}</small><strong>${item.value}</strong></div>`)
    .join('');
}

function renderChannels() {
  channelBars.innerHTML = channels
    .map(
      (item) => `
      <div class="bar-item">
        <span>${item.name}</span>
        <div class="track"><div class="fill" style="width:${item.value}%"></div></div>
        <b>${item.value}%</b>
      </div>`
    )
    .join('');
}

function renderSkus() {
  skuList.innerHTML = skus
    .map(
      (s) => `
      <div class="sku-card">
        <h3>${s.name}</h3>
        <div class="sku-meta">需求指数 ${s.demand} · 库存 ${s.stock}</div>
        <span class="sku-pill">${s.action}</span>
      </div>`
    )
    .join('');
}

function bindTabs() {
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => activateView(tab.dataset.view));
  });
}

function activateView(viewName) {
  tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.view === viewName));
  views.forEach((view) => view.classList.toggle('active', view.dataset.view === viewName));
}

function bindConfig() {
  document.getElementById('saveConfigBtn').addEventListener('click', () => {
    const config = saveConfig({
      botId: document.getElementById('botIdInput').value,
      apiKey: document.getElementById('apiKeyInput').value,
      baseUrl: document.getElementById('baseUrlInput').value
    });

    const state = config.botId && config.apiKey ? '已连接' : '配置不完整';
    document.getElementById('configState').textContent = state;
  });
}

function loadConfig() {
  const config = getConfig();
  if (!config) return;
  document.getElementById('botIdInput').value = config.botId || '';
  document.getElementById('apiKeyInput').value = config.apiKey || '';
  document.getElementById('baseUrlInput').value = config.baseUrl || 'https://api.coze.cn';

  if (config.botId && config.apiKey) {
    document.getElementById('configState').textContent = '已连接';
  }
}

function bindChat() {
  chatForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    pushBubble('user', text);
    chatInput.value = '';
    const loading = pushBubble('ai', 'AIRON 正在深度分析...');

    try {
      const answer = await sendToAIRON(text);
      loading.textContent = answer;
      appendStructuredAnswer(structuredAnswer);
    } catch {
      loading.textContent = '已切换演示模式回答：建议以高意向人群为核心做分层运营与预算动态分配。';
      appendStructuredAnswer(structuredAnswer);
    }

    chatWindow.scrollTop = chatWindow.scrollHeight;
  });
}

function pushBubble(type, content) {
  const node = document.createElement('div');
  node.className = `bubble ${type}`;
  node.textContent = content;
  chatWindow.appendChild(node);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return node;
}

function appendStructuredAnswer(answer) {
  const card = document.createElement('div');
  card.className = 'answer-card';
  card.innerHTML = `
    <h4>策略摘要</h4><p>${answer.summary}</p>
    <h4 style="margin-top:8px;">执行节奏</h4><p>${answer.strategy}</p>
    <h4 style="margin-top:8px;">风险提示</h4><p>${answer.risk}</p>
  `;
  chatWindow.appendChild(card);
}

async function startKeynote() {
  const scriptPrompt = '请基于近7日数据，给出“618预热”分阶段投放策略。';
  await typePrompt(scriptPrompt);

  activateView('settings');
  document.getElementById('botIdInput').value = 'AIRON-BOT-3827862316791411';
  document.getElementById('baseUrlInput').value = 'https://api.coze.cn';
  document.getElementById('apiKeyInput').value = 'sat_********************************';
  document.getElementById('configState').textContent = '已连接';
  await sleep(1000);

  activateView('copilot');
  await sleep(700);
  const keynoteQuestion = '请给我一份可落地的618预热增长方案，重点优化ROI和复购。';
  chatInput.value = '';
  await typeInput(chatInput, keynoteQuestion);
  pushBubble('user', keynoteQuestion);
  await sleep(500);
  pushBubble('ai', 'AIRON 建议：预算向高意向搜索+短视频倾斜 18%，并在私域触发分层召回。');
  appendStructuredAnswer(structuredAnswer);

  await sleep(1600);
  activateView('home');
  animateMetric('gmv', 2860000, 3180000, '¥ ');
  animateMetric('aicvr', 34.9, 37.6, '', '%');
  animateMetric('roi', 3.81, 4.22);
  animateMetric('fcr', 89.3, 91.4, '', '%');

  await sleep(1700);
  activateView('goods');
  await sleep(1700);
  activateView('service');
}

async function typePrompt(text) {
  promptText.textContent = '';
  for (const ch of text) {
    promptText.textContent += ch;
    await sleep(36);
  }
}

async function typeInput(input, text) {
  for (const ch of text) {
    input.value += ch;
    await sleep(20);
  }
}

function animateMetric(id, from, to, prefix = '', suffix = '') {
  const node = document.getElementById(id);
  const duration = 1200;
  const start = performance.now();

  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = from + (to - from) * eased;

    const display = Number.isInteger(to)
      ? Math.round(val).toLocaleString('zh-CN')
      : val.toFixed(2).replace(/\.00$/, '');

    node.textContent = `${prefix}${display}${suffix}`;

    if (p < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
