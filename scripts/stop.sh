#!/bin/bash
# Stop all Streamlit processes

echo "Stopping Streamlit..."
taskkill //F //IM streamlit.exe 2>/dev/null
sleep 1
echo "Done."
