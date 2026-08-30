FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install asyncpg for PostgreSQL async support
RUN pip install --no-cache-dir asyncpg psycopg2-binary alembic

# Copy the rest of the application
COPY . .

# Create static directory for rendered files
RUN mkdir -p static/edited

# Expose API port
EXPOSE 8000

# Run the app with uvicorn
# --http httptools     : uses the C-based httptools parser which has no hard body-size cap (unlike h11)
# --timeout-keep-alive : allow slow uploads up to 10 minutes before the connection is closed
# --limit-concurrency  : cap concurrent connections to avoid OOM on large parallel uploads
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--http", "httptools", "--timeout-keep-alive", "600", "--limit-concurrency", "20", "--reload"]
