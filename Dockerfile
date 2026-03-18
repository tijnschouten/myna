FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen

COPY src ./src

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "myna.main:app", "--host", "0.0.0.0", "--port", "8000"]
