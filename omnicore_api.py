from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
import uuid
import random
from datetime import datetime
from urllib import request as urlrequest
from urllib import error as urlerror
from urllib import parse as urlparse

# Existing tool logic
from ecommerce_service import track_order, get_personalized_push, get_product_info
from mcp_server import search_global_trends

app = FastAPI(
    title="OmniCore AI API",
    description="企业级电商 AI 平台 API：订单、推荐、趋势、连接器接入、AIRON 对话代理。",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Legacy request models
# -------------------------------
class OrderRequest(BaseModel):
    order_id: str


class PushRequest(BaseModel):
    user_interest: str


class TrendRequest(BaseModel):
    query: str


# -------------------------------
# Enterprise models
# -------------------------------
class ConnectorCreateRequest(BaseModel):
    platform: str
    endpoint: str
    auth_type: str = Field(default="Bearer Token")
    token: Optional[str] = None


class ConnectorTestRequest(BaseModel):
    method: str = Field(default="GET")


class AironChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


# -------------------------------
# In-memory enterprise store
# -------------------------------
CONNECTORS: List[Dict[str, Any]] = [
    {
        "id": str(uuid.uuid4()),
        "platform": "淘宝/天猫",
        "endpoint": "/api/merchant/taobao/orders",
        "auth_type": "Bearer Token",
        "status": "Connected",
        "last_update": "2s 前",
    },
    {
        "id": str(uuid.uuid4()),
        "platform": "京东",
        "endpoint": "/api/merchant/jd/inventory",
        "auth_type": "AppKey + Secret",
        "status": "Connected",
        "last_update": "4s 前",
    },
    {
        "id": str(uuid.uuid4()),
        "platform": "抖音电商",
        "endpoint": "/api/merchant/douyin/ads",
        "auth_type": "OAuth2",
        "status": "Syncing",
        "last_update": "刚刚",
    },
]

EVENTS: List[str] = [
    "[16:42:11] 订单事件流 +128",
    "[16:42:13] ROI 阈值触发告警",
    "[16:42:16] AIRON 生成预算调整建议",
    "[16:42:20] 客服 SLA 恢复到 95%",
]


# -------------------------------
# Helpers
# -------------------------------
def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def push_event(text: str) -> None:
    EVENTS.insert(0, f"[{now_ts()}] {text}")
    del EVENTS[30:]


def safe_json_load(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def coze_extract_answer(payload: Dict[str, Any]) -> Optional[str]:
    # Compatibility parsing for possible Coze response variants
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        messages = data.get("messages")
        if isinstance(messages, list):
            for item in messages:
                if item.get("type") == "answer" and item.get("content"):
                    return item.get("content")
        if isinstance(data.get("content"), str):
            return data.get("content")

    messages = payload.get("messages") if isinstance(payload, dict) else None
    if isinstance(messages, list):
        for item in messages:
            if item.get("type") == "answer" and item.get("content"):
                return item.get("content")

    if isinstance(payload.get("msg"), str):
        return payload.get("msg")

    return None


def coze_chat(message: str, user_id: str) -> str:
    api_key = os.getenv("COZE_API_KEY")
    bot_id = os.getenv("COZE_BOT_ID")
    base_url = os.getenv("COZE_API_BASE", "https://api.coze.cn")

    if not api_key:
        raise HTTPException(status_code=500, detail="COZE_API_KEY 未配置")
    if not bot_id:
        raise HTTPException(status_code=500, detail="COZE_BOT_ID 未配置")

    payload = {
        "bot_id": bot_id,
        "user_id": user_id,
        "stream": False,
        "additional_messages": [
            {
                "role": "user",
                "content": message,
                "content_type": "text",
            }
        ],
    }

    req = urlrequest.Request(
        url=f"{base_url}/v3/chat",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            created = safe_json_load(body) or {}

        # Some Coze bots return async status first (in_progress).
        data = created.get("data") if isinstance(created, dict) else {}
        chat_id = data.get("id")
        conversation_id = data.get("conversation_id")
        status = data.get("status")

        # Direct answer path (if present in create response).
        answer = coze_extract_answer(created)
        if answer:
            return answer

        if not chat_id or not conversation_id:
            return "AIRON 已收到请求，但缺少 chat/conversation 标识，无法继续轮询。"

        # Poll chat status until completed.
        for _ in range(15):
            if status in ("completed", "failed", "requires_action", "canceled"):
                break
            poll_query = urlparse.urlencode(
                {"conversation_id": conversation_id, "chat_id": chat_id}
            )
            poll_req = urlrequest.Request(
                url=f"{base_url}/v3/chat/retrieve?{poll_query}",
                headers={"Authorization": f"Bearer {api_key}"},
                method="GET",
            )
            with urlrequest.urlopen(poll_req, timeout=20) as poll_resp:
                poll_body = poll_resp.read().decode("utf-8", errors="ignore")
                polled = safe_json_load(poll_body) or {}
                status = ((polled.get("data") or {}).get("status")) or status
            if status == "completed":
                break

        # Fetch message list and extract assistant answer.
        msg_query = urlparse.urlencode(
            {"conversation_id": conversation_id, "chat_id": chat_id}
        )
        msg_req = urlrequest.Request(
            url=f"{base_url}/v3/chat/message/list?{msg_query}",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urlrequest.urlopen(msg_req, timeout=20) as msg_resp:
            msg_body = msg_resp.read().decode("utf-8", errors="ignore")
            msg_payload = safe_json_load(msg_body) or {}

        messages = msg_payload.get("data") if isinstance(msg_payload, dict) else []
        if isinstance(messages, list):
            for item in messages:
                if item.get("type") == "answer" and item.get("content"):
                    return item.get("content")

        # Fallback if completed but no answer message parsed.
        return "AIRON 已完成处理，但未解析到 answer 消息，请检查智能体输出。"
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
        raise HTTPException(status_code=502, detail=f"Coze HTTPError: {detail}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Coze 请求失败: {exc}")


# -------------------------------
# Health / Legacy APIs
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "OmniCore AI API is running", "version": "2.0.0"}


@app.get("/api/debug/env", summary="仅用于排查部署环境变量")
def debug_env():
    # 不返回密钥本身，只返回是否存在
    return {
        "has_COZE_API_KEY": bool(os.getenv("COZE_API_KEY")),
        "COZE_BOT_ID": os.getenv("COZE_BOT_ID"),
        "COZE_USER_ID": os.getenv("COZE_USER_ID"),
        "COZE_API_BASE": os.getenv("COZE_API_BASE"),
    }


@app.post("/api/track-order", summary="查询订单物流状态")
def api_track_order(req: OrderRequest):
    result = track_order(req.order_id)
    if isinstance(result, str) and "未找到" in result:
        raise HTTPException(status_code=404, detail=result)
    return result


@app.post("/api/personalized-push", summary="获取精准商品推荐")
def api_personalized_push(req: PushRequest):
    return get_personalized_push(req.user_interest)


@app.get("/api/product/{sku}", summary="获取特定商品详细信息")
def api_get_product(sku: str):
    result = get_product_info(sku)
    if isinstance(result, str) and "未在库中" in result:
        raise HTTPException(status_code=404, detail=result)
    return result


@app.post("/api/trends", summary="搜索全球电商趋势")
def api_trends(req: TrendRequest):
    return {"trends": search_global_trends(req.query)}


# -------------------------------
# Enterprise connector APIs
# -------------------------------
@app.get("/api/enterprise/connectors")
def get_connectors():
    return {"items": CONNECTORS}


@app.post("/api/enterprise/connectors")
def create_connector(req: ConnectorCreateRequest):
    item = {
        "id": str(uuid.uuid4()),
        "platform": req.platform,
        "endpoint": req.endpoint,
        "auth_type": req.auth_type,
        "status": "Pending",
        "last_update": "刚刚",
    }
    CONNECTORS.insert(0, item)
    push_event(f"新增连接器 {req.platform} -> {req.endpoint}")
    return item


@app.post("/api/enterprise/connectors/{connector_id}/test")
def test_connector(connector_id: str, req: ConnectorTestRequest):
    target = next((c for c in CONNECTORS if c["id"] == connector_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Connector not found")

    endpoint = target["endpoint"]
    # Relative path is treated as simulated healthy connector
    if endpoint.startswith("/"):
        target["status"] = "Connected"
        target["last_update"] = "刚刚"
        push_event(f"连接器健康检查通过（模拟）: {target['platform']}")
        return {"ok": True, "mode": "simulated", "status": target["status"]}

    # Real URL health check
    try:
        probe_req = urlrequest.Request(endpoint, method=req.method.upper())
        with urlrequest.urlopen(probe_req, timeout=6) as resp:
            ok = 200 <= resp.getcode() < 400
            target["status"] = "Connected" if ok else "Degraded"
            target["last_update"] = "刚刚"
            push_event(f"连接器健康检查 {'通过' if ok else '异常'}: {target['platform']}")
            return {"ok": ok, "http_status": resp.getcode(), "status": target["status"]}
    except Exception as exc:  # noqa: BLE001
        target["status"] = "Error"
        target["last_update"] = "刚刚"
        push_event(f"连接器健康检查失败: {target['platform']} ({exc})")
        return {"ok": False, "status": "Error", "detail": str(exc)}


@app.get("/api/enterprise/metrics")
def get_metrics():
    connected = sum(1 for c in CONNECTORS if c["status"] == "Connected")
    total = len(CONNECTORS) or 1
    online_ratio = round((connected / total) * 100, 1)

    gmv = 3200000 + random.randint(-80000, 120000)
    aicvr = round(35.0 + random.random() * 3.0, 1)
    fcr = round(88.5 + random.random() * 2.5, 1)
    risk = max(20, 80 - connected * 3 + random.randint(-6, 6))

    channels = [
        {"label": "订单吞吐", "value": min(99, 70 + connected * 4 + random.randint(-5, 5))},
        {"label": "客服请求", "value": min(99, 60 + random.randint(-8, 8))},
        {"label": "投放转化", "value": min(99, 66 + connected * 3 + random.randint(-5, 6))},
        {"label": "库存健康", "value": min(99, 82 + random.randint(-4, 4))},
    ]

    return {
        "kpis": {
            "gmv": gmv,
            "aicvr": aicvr,
            "fcr": fcr,
            "risk": risk,
            "connector_online_ratio": online_ratio,
        },
        "channels": channels,
    }


@app.get("/api/enterprise/events")
def get_events():
    return {"items": EVENTS[:20]}


# -------------------------------
# AIRON Coze proxy
# -------------------------------
@app.post("/api/enterprise/airon/chat")
def airon_chat(req: AironChatRequest):
    user_id = req.user_id or os.getenv("COZE_USER_ID", "user9093316760")
    answer = coze_chat(req.message, user_id)
    push_event("AIRON 已返回策略建议")
    return {"answer": answer, "user_id": user_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
