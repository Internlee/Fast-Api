FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed for Playwright browsers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
        libxcomposite1 libxdamage1 libxfixes3 \
        libxrandr2 libxshmfence1 libx11-6 libx11-xcb1 \
        libxcb1 libxcb-shm0 libxcb-dri3-0 \
        libxext6 libxrender1 libxinerama1 libxcursor1 \
        libxi6 libgtk-3-0 libgdk-pixbuf-2.0-0 \
        libpangocairo-1.0-0 libpango-1.0-0 \
        fontconfig libfreetype6 libasound2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
	python -m playwright install chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

