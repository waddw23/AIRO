# 使用轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# HuggingFace Spaces（Docker）不会自动注入 PORT，这里固定 7860 并兼容外部注入
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn omnicore_api:app --host 0.0.0.0 --port ${PORT:-7860}"]
