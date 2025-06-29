FROM python:3.11-slim

# ────────────────────────────────────────────────────────────────
# Install optional system deps (tzdata needed by `holidays`)
# ────────────────────────────────────────────────────────────────
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential tzdata \
    && rm -rf /var/lib/apt/lists/*

# ────────────────────────────────────────────────────────────────
# Create app directory
# ────────────────────────────────────────────────────────────────
WORKDIR /app

# ────────────────────────────────────────────────────────────────
# Install Python dependencies first (better layer caching)
# ────────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ────────────────────────────────────────────────────────────────
# Copy the rest of the application code
# ────────────────────────────────────────────────────────────────
COPY . .

# ────────────────────────────────────────────────────────────────
# Environment vars for Streamlit (headless, 0.0.0.0, port 8501)
# ────────────────────────────────────────────────────────────────
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

# ────────────────────────────────────────────────────────────────
# Default command
# ────────────────────────────────────────────────────────────────
CMD ["streamlit", "run", "urenregistratie_moneybird.py"]
