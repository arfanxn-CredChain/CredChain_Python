# Single-stage runtime image.
# Models are NOT baked in — they are mounted as Docker volumes at runtime.
# Run `make download-models` once on the host before `make docker-up-build`.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget build-essential cmake && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
       --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

COPY app/ ./app/
COPY locales/ ./locales/

RUN chown -R app:app /app
USER app

ENV MODEL_DIR=/models
ENV PYTHONUNBUFFERED=1

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD wget -qO- http://localhost:8081/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
