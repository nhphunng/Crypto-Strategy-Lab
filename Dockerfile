FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY backend/pyproject.toml /build/pyproject.toml
COPY backend/requirements.runtime.lock /build/requirements.runtime.lock
RUN python -m pip install --prefix=/install --requirement requirements.runtime.lock
COPY backend/src /build/src
RUN python -m pip install --prefix=/install --no-deps .
COPY backend/requirements.sentiment.lock /build/requirements.sentiment.lock
RUN python -m pip install --prefix=/install --constraint requirements.runtime.lock --requirement requirements.sentiment.lock
COPY backend/scripts/cache_sentiment_model.py /build/cache_sentiment_model.py
RUN PYTHONPATH=/install/lib/python3.12/site-packages python cache_sentiment_model.py /models/finbert

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH

RUN groupadd --system --gid 65532 app && useradd --system --uid 65532 --gid app --create-home app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --from=builder --chown=65532:65532 /models/finbert /opt/models/finbert
ENV CSL_SENTIMENT_MODEL_PATH=/opt/models/finbert
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/migrations /app/backend/migrations
COPY backend/sandbox /app/backend/sandbox
COPY infra/security /app/infra/security

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
CMD ["uvicorn", "crypto_lab.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
