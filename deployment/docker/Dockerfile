FROM python:3.12-slim AS runtime

# 安装 Sherpa-ONNX 依赖库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libsndfile1-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY knowledge /app/knowledge
COPY frontend-console/dist /app/frontend-console/dist
COPY frontend-h5/dist /app/frontend-h5/dist
COPY scripts /app/scripts

# 创建模型目录并下载离线语音模型
RUN mkdir -p /app/backend/models && \
    python /app/scripts/download_sherpa_models.py --all

WORKDIR /app/backend

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

