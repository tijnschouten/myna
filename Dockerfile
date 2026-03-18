FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
RUN uv sync --no-dev

COPY src ./src

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "myna.main:app", "--host", "0.0.0.0", "--port", "8000"]
