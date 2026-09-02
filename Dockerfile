# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev is required for psycopg2 (Postgres driver)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment inside the container
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project
RUN poetry install --no-interaction --no-ansi

# Expose port
EXPOSE 8000

# The CMD is overridden by the 'command' in your docker-compose.yml
CMD ["poetry", "run", "uvicorn", "notification_service.main:main", "--factory", "--host", "0.0.0.0", "--port", "8000"]