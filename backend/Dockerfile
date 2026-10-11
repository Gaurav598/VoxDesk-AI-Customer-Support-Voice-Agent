FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HOST=0.0.0.0 \
    PORT=8088 \
    DATABASE_PATH=/app/data/voice_agent.db

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ ./src/
COPY scripts/ ./scripts/

RUN mkdir -p /app/data

EXPOSE 8088

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/health')" || exit 1

CMD ["python", "scripts/run_local_server.py"]
