# Base image
FROM python:3.11-slim

# Working directory inside the container

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

RUN chmod +x scripts/startup.sh

# Expose port FastAPI runs on
EXPOSE 8000

# Start the app
CMD ["./scripts/startup.sh"]