FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends wget && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --default-timeout=600 torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml .
COPY app/ app/
COPY locales/ locales/

RUN pip install --no-cache-dir -e "."

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD wget -qO- http://localhost:8081/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
