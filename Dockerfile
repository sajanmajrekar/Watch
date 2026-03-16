# Dockerfile for Watch Banner Generator
# This is designed for deployment on platforms that support Docker (Render, Railway, Fly.io, etc.)

FROM python:3.12-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Copy requirements first to leverage layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create output directory
RUN mkdir -p /app/output

# Expose the port the app listens on
EXPOSE 5001

# Run the app
CMD ["python", "app.py"]
