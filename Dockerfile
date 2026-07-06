FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose Hugging Face Spaces port
EXPOSE 7860

# Start FastAPI app - rebuild vectorstores first, then start server
CMD ["sh", "-c", "python app/utils/rebuild_vectorstores.py && uvicorn app.app:app --host 0.0.0.0 --port 7860"]