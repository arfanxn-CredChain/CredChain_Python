# Multi-stage build: models baked into image (no host volume mount).
#
# Stage 1 downloads EasyOCR + LaBSE weights (~1.95 GB) once.
# Stage 2 is the lean runtime image, copying weights from stage 1.

FROM python:3.11-slim AS model-downloader

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir easyocr==1.7.2 sentence-transformers==3.3.1

WORKDIR /models

RUN python -c "import easyocr; easyocr.Reader(['id','en'], \
    model_storage_directory='/models/easyocr', download_enabled=True)"

RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/LaBSE').save('/models/labse')"


FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
       --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

COPY --from=model-downloader /models /models
COPY app/ ./app/
COPY locales/ ./locales/

RUN chown -R app:app /app /models
USER app

ENV MODEL_DIR=/models
ENV PYTHONUNBUFFERED=1

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD wget -qO- http://localhost:8081/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
