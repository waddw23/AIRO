
import sys
import os

# Import the tool logic from the files
from ecommerce_service import track_order, get_personalized_push, get_product_info
from mcp_server import search_global_trends

def run_demonstration():
    print("=== OMNICORE AI ACTION DEMONSTRATION ===\n")

    # 1. Track Order
    print("Action: Tracking Order 'ORD101'...")
    order_result = track_order("ORD101")
    print(f"Result: {order_result}\n")

    # 2. Precision Push (In-DB Match)
    interest = "智能恒温杯"
    print(f"动作: 库内匹配精准推送 '{interest}'...")
    push_result = get_personalized_push(interest)
    print(f"结果: {push_result}\n")

    # 3. Precision Push (Real-time Fallback)
    new_interest = "最新款国产折叠屏手机"
    print(f"动作: 全网实时搜索推送 '{new_interest}'...")
    try:
        live_push_result = get_personalized_push(new_interest)
        print(f"结果: {live_push_result}\n")
    except Exception as e:
        print(f"实时搜索动作 (需联网): {e}\n")

    # 4. Product Info
    sku = "SKU003"
    print(f"动作: 获取商品信息 '{sku}'...")
    sku_result = get_product_info(sku)
    print(f"结果: {sku_result}\n")

    # 4. Search trends
    market = "Europe"
    print(f"Action: searching trends for '{market}'...")
    # Mocking search_global_trends since DDGS might require network
    try:
        trends_result = search_global_trends(market)
        print(f"Result: {trends_result}\n")
    except Exception as e:
        print(f"Trend Search Action (requires internet): {e}\n")

if __name__ == "__main__":
    run_demonstration()
