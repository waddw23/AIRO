# AIRON Commerce AI Frontend

企业级电商 AI 平台前端演示版，内置运营看板、AI Copilot、商品洞察、自动化策略和客服中台模块。

## 目录

- `index.html`：主页面
- `styles.css`：视觉系统与响应式布局
- `js/app.js`：交互逻辑
- `js/cozeClient.js`：Coze API 封装

## 快速使用

1. 直接在浏览器打开 `index.html`，或使用本地静态服务：
   ```bash
   cd frontend
   python3 -m http.server 8080
   ```
2. 打开 `http://localhost:8080`
3. 进入「集成设置」，填入：
   - `Bot ID`：AIRON 对应 Bot ID
   - `API Key`：Coze PAT
   - `API Base URL`：默认 `https://api.coze.cn`
4. 保存后进入「运营 Copilot」发起对话。

## 安全建议（生产环境）

- 不要在前端长期持有真实 API Key。
- 推荐在后端实现 `/api/airon/chat` 代理，由服务端注入密钥并做权限校验。
- 对高价值操作增加审批流与审计日志。

## 可扩展方向

- 接入你现有的订单/商品/客服系统接口，替换示例数据。
- 增加多角色权限（运营、客服主管、管理员）。
- 将 AI 输出结构化为「策略卡片 + 任务清单 + 执行追踪」。
