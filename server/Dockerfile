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

CMD ["python", "app.py"]
