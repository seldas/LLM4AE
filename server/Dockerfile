FROM python:3.11-slim

WORKDIR /app

# Install dependencies in the image
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Development fallback: ensure app.py can run even if volume isn't mounted yet
COPY . .

EXPOSE 8862

# Default command (overridden in dev compose)
CMD ["python", "app.py"]
