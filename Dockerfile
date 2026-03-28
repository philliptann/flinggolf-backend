FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*
  
COPY docker/entrypoint.sh /entrypoint.sh 
RUN chmod +x /entrypoint.sh

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code (includes templates/ and static/)
COPY . /app
# Code will be bind-mounted in docker-compose for dev.
