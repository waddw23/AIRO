const STORAGE_KEY = "airon_coze_config";

export function getConfig() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveConfig(config) {
  const payload = {
    botId: config.botId?.trim(),
    apiKey: config.apiKey?.trim(),
    baseUrl: config.baseUrl?.trim() || "https://api.coze.cn"
  };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  return payload;
}

export async function sendToAIRON(message) {
  const config = getConfig();
  if (!config?.apiKey || !config?.botId) {
    throw new Error("请先在集成设置里填写 Bot ID 与 API Key。");
  }

  const resp = await fetch(`${config.baseUrl}/v3/chat`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${config.apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      bot_id: config.botId,
      user_id: "enterprise-console-user",
      stream: false,
      additional_messages: [
        {
          role: "user",
          content: message,
          content_type: "text"
        }
      ]
    })
  });

  if (!resp.ok) {
    const err = await safeParse(resp);
    const detail = err?.msg || err?.message || `HTTP ${resp.status}`;
    throw new Error(`AIRON 请求失败：${detail}`);
  }

  const data = await resp.json();
  const fallback = "已收到请求。建议你开启结构化 prompt，以便我输出可执行运营方案。";

  // Coze 响应结构可能因版本差异而变化，这里做兼容解析。
  return (
    data?.data?.messages?.find((m) => m.type === "answer")?.content ||
    data?.messages?.find((m) => m.type === "answer")?.content ||
    data?.data?.content ||
    fallback
  );
}

async function safeParse(resp) {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}
