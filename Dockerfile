FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for SAST tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install optional SAST tools
RUN pip install --no-cache-dir bandit pip-audit && \
    npm install -g eslint semgrep 2>/dev/null || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install the package (if setup.py/pyproject.toml exists)
RUN pip install -e . 2>/dev/null || true

EXPOSE 8000 8501

# Default: Streamlit UI. Override for API: --backend
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
