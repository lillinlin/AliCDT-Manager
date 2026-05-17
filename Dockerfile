FROM python:3.12-slim

WORKDIR /app

# 安装后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建产物（由 CI 在 Actions 中提前构建）
COPY frontend/dist/ ./frontend/dist/

# 数据目录
RUN mkdir -p /app/data

WORKDIR /app/backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
