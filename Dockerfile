# 使用轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 启动命令：优先使用平台注入的 PORT，默认为 8000
CMD ["sh", "-c", "uvicorn omnicore_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
