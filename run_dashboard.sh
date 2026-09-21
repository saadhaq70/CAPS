#!/bin/bash
# Launch ASH-FL Interactive Dashboard

echo "=========================================="
echo "ASH-FL Interactive Dashboard"
echo "=========================================="
echo ""
echo "Starting Streamlit server..."
echo "Dashboard will open at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

streamlit run dashboard_app.py
