# Use Linux Python, no Conda, clean and boring
FROM python:3.11-slim

# Avoid .pyc files and make logs unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create work dir
WORKDIR /app

# System deps (psycopg, build, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    nano \
    less \
    iputils-ping \
    postgresql-client \
    redis-tools \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . .

# Whatever your app uses, e.g. DATABASE_URL etc.
ENV PORT=8000

# Expose port (optional but nice)
EXPOSE 8000

# Run FastAPI app; adjust "main:app" if your entrypoint is different
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]