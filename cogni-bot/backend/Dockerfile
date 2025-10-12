# Use Python 3.11 slim image
FROM python:3.11-slim

# Install build tools
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Set port
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Use Gunicorn to run the app
CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "--threads", "8", "--timeout", "0", "main:app"]