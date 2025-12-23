FROM python:3.11-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Remove any Python cache
RUN find . -type d -name __pycache__ -exec rm -r {} + || true
RUN find . -type f -name "*.pyc" -delete || true

EXPOSE 87

CMD ["python", "app.py"]