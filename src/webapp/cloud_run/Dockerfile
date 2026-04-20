FROM python:3.13-slim
RUN pip install uv

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
COPY src/webapp/cloud_run ./src/webapp/cloud_run

RUN uv sync --frozen --package webapp_push_to_google_ads --no-dev

ENTRYPOINT ["uv", "run", "--package", "webapp_push_to_google_ads", "python", "src/webapp/cloud_run/main.py"]
