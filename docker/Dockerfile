FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system agentmesh && adduser --system --ingroup agentmesh agentmesh

COPY pyproject.toml alembic.ini README.md ./
COPY backend ./backend

RUN pip install --upgrade pip && pip install .

RUN chown -R agentmesh:agentmesh /app
USER agentmesh

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

