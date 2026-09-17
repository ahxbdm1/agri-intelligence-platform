FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --default-timeout=120 --retries=8 \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    -r /app/backend/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts
COPY knowledge_base /app/knowledge_base
COPY data /app/data

ENV PYTHONPATH=/app:/app/backend

CMD ["uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
