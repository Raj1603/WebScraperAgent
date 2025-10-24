# ---------- BASE IMAGE ----------
FROM python:3.11-slim

# ---------- SYSTEM DEPENDENCIES ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl wget gnupg git \
    # Browser + graphics dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 \
    libx11-6 libx11-xcb1 libxext6 libxfixes3 libxrender1 \
    libxcb1 libatspi2.0-0 libcairo2 libpango-1.0-0 \
    libglib2.0-0 libgobject-2.0-0 libgio-2.0-0 libdbus-1-3 libexpat1 \
    fonts-liberation xvfb && \
    rm -rf /var/lib/apt/lists/*

# ---------- SETUP ENV ----------
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8080

# ---------- INSTALL PYTHON DEPS ----------
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m playwright install --with-deps chromium

# ---------- COPY PROJECT ----------
COPY . .

# ---------- EXPOSE PORT ----------
EXPOSE 8080

# ---------- RUN SERVER ----------
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
