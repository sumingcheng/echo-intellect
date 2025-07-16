FROM python:3.10-slim

WORKDIR /code

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv sync

ENV PATH="/code/.venv/bin:${PATH}"

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app", "--host", "0.0.0.0", "--port", "50000"]