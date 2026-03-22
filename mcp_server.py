from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS

# Initialize the MCP Server
mcp = FastMCP("OmniCore_Trends")

@mcp.tool()
def search_global_trends(query: str):
    """
    Finds the latest hot-selling product categories and consumer trends. 
    Use this when users ask for market insights or 'what to sell'.
    """
    with DDGS() as ddgs:
        # 针对国内电商趋势进行搜索
        results = [r for r in ddgs.text(f"2025国内电商爆款 抖音 小红书 {query}", max_results=3)]
    
    # Format for LLM readability
    formatted_results = []
    for r in results:
        formatted_results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nSource: {r['href']}")
    return "\n---\n".join(formatted_results)

@mcp.tool()
def analyze_market_fit(product_name: str, region: str):
    """
    Simulates a market fit analysis for a specific product and region.
    """
    # Logic to be expanded with real API calls
    return {
        "product": product_name,
        "region": region,
        "status": "High Potential",
        "reason": "Rising search volume in TikTok/Pinterest for this category."
    }

if __name__ == "__main__":
    mcp.run()
