FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file first (Docker layer caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose service port
EXPOSE 86

# Run the Flask app
CMD ["python", "app.py"]
