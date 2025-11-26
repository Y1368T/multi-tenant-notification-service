# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# Use minimal install for faster build
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    # Clean up to keep the image small
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install production dependencies (without the project itself yet)
# We use a dedicated install layer for dependencies that won't change often
RUN poetry install --no-root --only main

# Copy application code AFTER dependency install to leverage Docker cache
COPY . .

# --- CRITICAL FIX: Set PYTHONPATH to include the 'src' directory ---
ENV PYTHONPATH="/app/src:${PYTHONPATH}"

# (Optional but recommended) Install the project code in the current environment
# This will install your local project code (notification_service) itself
RUN poetry install --no-interaction --no-ansi --no-dev 

# Expose port
EXPOSE 8000

# Run the application
# Note: You were using `notification_service.main:main` but Uvicorn typically expects the FastAPI/Starlette app object, often named `app`. I'll assume your main object is correctly named.
CMD ["poetry", "run", "uvicorn", "notification_service.main:main","--factory","--host", "0.0.0.0", "--port", "8000"]