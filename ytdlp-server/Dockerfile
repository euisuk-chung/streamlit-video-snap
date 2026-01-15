FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp, Flask, and LLM dependencies
RUN pip install --no-cache-dir yt-dlp flask flask-cors gunicorn requests \
    openai anthropic google-generativeai pyyaml

# Create app directory
WORKDIR /app

# Copy application files
COPY app.py .
COPY llm_service.py .

# Expose port
EXPOSE 8080

# Run with gunicorn (increased timeout for long videos)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--threads", "2", "--timeout", "600", "app:app"]
