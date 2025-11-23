FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp and Flask
RUN pip install --no-cache-dir yt-dlp flask flask-cors gunicorn

# Create app directory
WORKDIR /app

# Copy application files
COPY app.py .

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
