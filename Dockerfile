# Use the official Playwright image so Chromium + deps are preinstalled
FROM mcr.microsoft.com/playwright/python:v1.42.0-focal

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure browsers are up to date (noop if already bundled)
RUN playwright install

# Expose default FastAPI port
EXPOSE 8000

# Launch the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
