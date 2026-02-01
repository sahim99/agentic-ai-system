# Base Image
FROM python:3.9-slim

# Working Directory
WORKDIR /app

# Install Dependencies
# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Codebase
COPY . .

# Expose ports for both API and UI
EXPOSE 8000
EXPOSE 8501

# Default Command (Overridden by docker-compose)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
