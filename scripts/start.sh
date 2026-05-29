#!/bin/bash
# Start Streamlit — ensures only one instance runs

cd "$(dirname "$0")/.."

# Kill any existing streamlit on port 8501
echo "Stopping any existing Streamlit..."
taskkill //F //IM streamlit.exe 2>/dev/null
sleep 2

# Start fresh
echo "Starting Streamlit..."
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"
streamlit run app.py --server.port 8501 --server.headless true
