# ---------- BASE IMAGE ----------
FROM python:3.11-slim

# ---------- SYSTEM DEPENDENCIES ----------
RUN apt-get update && \
    apt-get install -y curl wget gnupg git libnss3 libatk-bridge2.0-0 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 \
    libgtk-3-0 fonts-liberation libxss1 libxtst6 libappindicator3-1 lsb-release \
    chromium chromium-driver xvfb && \
    rm -rf /var/lib/apt/lists/*

# ---------- SETUP ENV ----------
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ---------- INSTALL PYTHON DEPS ----------
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ---------- INSTALL PLAYWRIGHT CHROMIUM ----------
RUN python -m playwright install --with-deps chromium

# ---------- COPY PROJECT ----------
COPY . .

# ---------- EXPOSE PORT ----------
EXPOSE 8080

# ---------- RUN SERVER ----------
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
