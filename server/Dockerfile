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
# We use 4 workers and a longer timeout (120s) because LLM/BERT tasks can be heavy.
# Added logging flags to ensure backend output is visible.
CMD ["gunicorn", "--bind", "0.0.0.0:8862", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "app:app"]
