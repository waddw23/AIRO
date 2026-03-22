# AIRON 公网部署（Render + Cloudflare Pages）

## 1. 部署后端到 Render（永久免费试用层）

1. 把本项目推到 GitHub（根目录包含 `render.yaml`）。
2. 进入 Render: `New +` -> `Blueprint`（推荐）或 `Web Service`。
3. 选择这个 GitHub 仓库，Render 会自动识别 `render.yaml`。
4. 在环境变量中填入：
   - `COZE_API_KEY`: 你的 `sat_...`
   - `COZE_BOT_ID`: `7619599264641089582`（已默认）
   - `COZE_USER_ID`: `user9093316760`（已默认）
5. 等待部署完成，记下后端 URL，例如：
   - `https://airon-omnicore-api.onrender.com`

## 2. 部署前端到 Cloudflare Pages（长期可访问）

1. 打开 Pages，选择 `Create project` -> `Direct Upload`。
2. 上传 `/Users/Zhuanz/Desktop/001/deploy/airon-site.zip`。
3. 发布后得到 URL，例如：
   - `https://airon-enterprise.pages.dev`

## 3. 让前端连上你的公网 API

你有两种方式：

1. 最简单：在访问地址后拼接参数  
   - `https://airon-enterprise.pages.dev/?api=https://airon-omnicore-api.onrender.com`
2. 或者打开页面后，在右上角 `API` 输入框填后端地址并点 `应用`。

