FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=2 \
    UVICORN_PORT=8000 \
    UVICORN_HOST=0.0.0.0

WORKDIR /app

# Обновим pip и поставим зависимости (bcrypt/passlib зафиксированы в requirements.txt)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Код приложения
COPY . .

EXPOSE 8000

# healthcheck точка, если есть
# HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "${UVICORN_HOST}", "--port", "${UVICORN_PORT}", "--workers", "${UVICORN_WORKERS}"]

