import json
from omnicore_api import app

# 导出 OpenAPI JSON
with open("openapi.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

print("OpenAPI schema generated: openapi.json")
