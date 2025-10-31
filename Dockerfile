# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project
RUN poetry install --no-interaction --no-ansi

# Expose port
EXPOSE 8000

# Run the application
CMD ["poetry", "run", "uvicorn", "notification_service.main:main","--factory","--host", "0.0.0.0", "--port", "8000"]
