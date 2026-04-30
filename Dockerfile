# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY playlists.yaml .

# Create volume mount points for downloads
RUN mkdir -p /mnt/UBERVAULT/Music \
    /mnt/UBERVAULT/Video \
    /mnt/UBERVAULT/Torrents/Local

# Create a non-root user for security with same UID as host user
RUN useradd -m -u 1000 ytdl && \
    chown -R ytdl:ytdl /app

# Switch to non-root user
USER ytdl

# Default command
CMD ["python", "main.py"]
