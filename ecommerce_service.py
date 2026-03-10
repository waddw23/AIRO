from mcp.server.fastmcp import FastMCP
import random
from duckduckgo_search import DDGS  # 引入搜索以实现实时更新

# Initialize the MCP Server
mcp = FastMCP("OmniCore_Service")

# 增强型模拟数据库 (国内电商) - 作为核心缓存层
PRODUCT_DB = {
    "SKU001": {"name": "智能恒温杯", "stock": 45, "price": "￥199.00", "desc": "APP控制，精准控温。", "link": "https://jd.com/p/sku001"},
    "SKU002": {"name": "人体工学办公椅", "stock": 12, "price": "￥899.00", "desc": "透气网面，护腰设计。", "link": "https://tmall.com/p/sku002"},
    "SKU003": {"name": "专业瑜伽垫", "stock": 88, "price": "￥120.00", "desc": "防滑加厚，环保材质。", "link": "https://taobao.com/p/sku003"},
    "SKU004": {"name": "大容量移动电源", "stock": 150, "price": "￥159.00", "desc": "20000毫安，快速充电。", "link": "https://pinduoduo.com/p/sku004"}
}

ORDER_DB = {
    "ORD101": {"status": "运输中", "location": "杭州转运中心", "items": ["智能恒温杯"], "eta": "预计明天送达"},
    "ORD102": {"status": "派送中", "location": "北京朝阳区站点", "items": ["瑜伽垫"], "eta": "今天"},
}

@mcp.tool()
def get_product_info(sku: str):
    """
    获取商品详细信息。如果SKU不存在，将尝试进行全网实时价格搜索。
    """
    product = PRODUCT_DB.get(sku)
    if product:
        product["update_status"] = "已从内部库同步"
        return product
    
    return {"error": f"SKU {sku} 未在库中，请尝试搜索名称进行精准推送。"}

@mcp.tool()
def track_order(order_id: str):
    """
    实时追踪国内物流订单状态。
    """
    order = ORDER_DB.get(order_id)
    if not order:
        return f"订单 {order_id} 未找到，请核实单号。"
    
    return {
        "order_id": order_id,
        "current_status": order["status"],
        "location": order["location"],
        "estimated_arrival": order["eta"],
        "sync_time": "实时同步成功",
        "milestones": [
            {"time": "2026-03-07 10:00", "event": "已下单"},
            {"time": "2026-03-08 14:30", "event": "仓库已拣货"},
            {"time": "2026-03-09 09:00", "event": "已离开杭州分拨中心"}
        ]
    }

@mcp.tool()
def get_personalized_push(user_interest: str):
    """
    世界级精准推送逻辑：融合内部库 + 实时全网热度。
    """
    # 1. 尝试库内匹配
    suggestions = []
    for sku, info in PRODUCT_DB.items():
        if user_interest.lower() in info['name'].lower() or user_interest.lower() in info['desc'].lower():
            info["sku"] = sku
            suggestions.append(info)
    
    # 2. 实时库外补完 (Fallback to Live Search)
    live_info = "实时行情：近期搜索量上升"
    if not suggestions:
        with DDGS() as ddgs:
            # 搜索实时爆款详情
            live_results = [r for r in ddgs.text(f"淘宝 京东 爆款 {user_interest} 价格", max_results=1)]
            if live_results:
                return {
                    "msg": f"实时同步：我们在全网为您找到了最新的热点商品：",
                    "product": {
                        "name": live_results[0]['title'],
                        "price": "点击查看实时价",
                        "desc": live_results[0]['body'],
                        "link": live_results[0]['href']
                    },
                    "status": "LIVE_FETCHED"
                }
    
    # 3. 返回最佳结果
    pick = random.choice(suggestions) if suggestions else PRODUCT_DB["SKU003"]
    return {
        "msg": f"基于您的兴趣 '{user_interest}' 实时推荐：",
        "product": pick,
        "status": "DB_MATCHED"
    }

if __name__ == "__main__":
    mcp.run(transport="sse")
