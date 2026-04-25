FROM python:3.11-slim

WORKDIR /app

# Install dependencies with cache mount to speed up rebuilds
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Development fallback
COPY . .

EXPOSE 8862

# Use gunicorn for production. 
# We use eventlet worker class for WebSocket support.
# Single worker is recommended for Socket.io unless a message broker (Redis) is used.
CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", "--bind", "0.0.0.0:8862", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "app:app"]
