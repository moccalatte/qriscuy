# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies required by Pillow / uvloop
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends build-essential libjpeg62-turbo-dev zlib1g-dev \ 
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \ 
    && pip install -r requirements.txt

COPY app ./app

# Expose port for the FastAPI service
EXPOSE 8000

# Use environment variables to configure runtime secrets
ENV QRISCUY_MODE=SAFE

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
