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
    """
    尽可能从 Coze 返回中提取可读文本。
    优先级：data.messages.answer -> data.messages.any -> data.content -> messages.answer -> messages.any -> msg。
    """
    if not isinstance(payload, dict):
        return None

    def first_text(items):
        for it in items:
            if isinstance(it, dict):
                if it.get("type") == "answer" and it.get("content"):
                    return it.get("content")
                if isinstance(it.get("content"), str):
                    return it.get("content")
        return None

    data = payload.get("data")
    if isinstance(data, dict):
        msgs = data.get("messages")
        if isinstance(msgs, list):
            text = first_text(msgs)
            if text:
                return text
        if isinstance(data.get("content"), str):
            return data.get("content")

    msgs = payload.get("messages")
    if isinstance(msgs, list):
        text = first_text(msgs)
        if text:
            return text

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
        "user": user_id,
        "query": message,
        "stream": True,
    }

    req = urlrequest.Request(
        url=f"{base_url}/v1/chat",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            # SSE 流式响应
            answer_parts = []
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    data_str = line.replace("data:", "", 1).strip()
                    # 跳过 keepalive 或非 JSON
                    if not data_str or data_str == "[DONE]":
                        continue
                    data_obj = safe_json_load(data_str)
                    if isinstance(data_obj, dict):
                        # v1 流式 delta
                        content = data_obj.get("content")
                        if isinstance(content, str):
                            answer_parts.append(content)
                        # conversation.message.completed 场景
                        msg = data_obj.get("message")
                        if isinstance(msg, dict):
                            if isinstance(msg.get("content"), str):
                                answer_parts.append(msg["content"])
                            if isinstance(msg.get("content"), list):
                                for seg in msg["content"]:
                                    if isinstance(seg, str):
                                        answer_parts.append(seg)
                                    elif isinstance(seg, dict) and isinstance(seg.get("text"), str):
                                        answer_parts.append(seg["text"])
            if answer_parts:
                return "".join(answer_parts)
            # 尝试从最终块里取日志等信息
            try:
                fallback_raw = data_obj  # 最后一次 data_obj
                logid = (
                    fallback_raw.get("detail", {}).get("logid")
                    if isinstance(fallback_raw, dict)
                    else None
                )
            except Exception:
                logid = None
            msg = "Coze 返回为空，未获取到文本"
            if logid:
                msg += f"（logid: {logid}）"
            return msg
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
